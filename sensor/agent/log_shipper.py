#!/usr/bin/env python3
"""
HungryHoundDog Log Shipper Agent

Monitors Suricata's EVE JSON output, batches events, and ships them to the
Brain server via HTTPS POST with retry and exponential backoff logic.

This agent runs on the Raspberry Pi 4 sensor node and continuously forwards
security events to the central analysis server.
"""

import json
import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import yaml

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests library not found. Install with: pip install requests pyyaml")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/hungryhounddog/log_shipper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ShipperConfig:
    """Configuration for the log shipper agent"""
    brain_endpoint: str
    brain_api_key: str
    ship_interval: int
    batch_size: int
    health_check_interval: int
    eve_log_path: str
    seek_file_path: str
    verify_ssl: bool
    retry_attempts: int
    retry_backoff_factor: float
    connect_timeout: int
    read_timeout: int
    sensor_id: str
    sensor_name: str

    @staticmethod
    def from_yaml(config_file: str) -> 'ShipperConfig':
        """Load configuration from YAML file"""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        agent_config = config_data.get('agent', {})
        return ShipperConfig(
            brain_endpoint=agent_config.get('brain_endpoint', 'https://brain.hungryhounddog.local/api/events'),
            brain_api_key=agent_config.get('brain_api_key', ''),
            ship_interval=agent_config.get('ship_interval', 30),
            batch_size=agent_config.get('batch_size', 100),
            health_check_interval=agent_config.get('health_check_interval', 60),
            eve_log_path=agent_config.get('eve_log_path', '/var/log/suricata/eve.json'),
            seek_file_path=agent_config.get('seek_file_path', '/var/lib/hungryhounddog/eve.seek'),
            verify_ssl=agent_config.get('verify_ssl', True),
            retry_attempts=agent_config.get('retry_attempts', 3),
            retry_backoff_factor=agent_config.get('retry_backoff_factor', 2.0),
            connect_timeout=agent_config.get('connect_timeout', 10),
            read_timeout=agent_config.get('read_timeout', 30),
            sensor_id=agent_config.get('sensor_id', 'sensor-001'),
            sensor_name=agent_config.get('sensor_name', 'RPi4-Sensor-01')
        )


class EventBatch:
    """Represents a batch of events ready for shipping"""
    
    def __init__(self, config: ShipperConfig):
        self.config = config
        self.events: List[Dict[str, Any]] = []
        self.batch_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
        self.created_at = datetime.utcnow().isoformat()
    
    def add_event(self, event: Dict[str, Any]) -> None:
        """Add event to batch"""
        self.events.append(event)
    
    def is_full(self) -> bool:
        """Check if batch has reached maximum size"""
        return len(self.events) >= self.config.batch_size
    
    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if batch is older than max age"""
        created = datetime.fromisoformat(self.created_at)
        age = (datetime.utcnow() - created).total_seconds()
        return age > max_age_seconds
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert batch to API payload"""
        return {
            'batch_id': self.batch_id,
            'sensor_id': self.config.sensor_id,
            'sensor_name': self.config.sensor_name,
            'timestamp': datetime.utcnow().isoformat(),
            'event_count': len(self.events),
            'events': self.events
        }


class SeekTracker:
    """Tracks file position in EVE log for resumable reading"""
    
    def __init__(self, seek_file: str):
        self.seek_file = seek_file
        self.position = 0
        self._load_seek()
    
    def _load_seek(self) -> None:
        """Load saved position from seek file"""
        if os.path.exists(self.seek_file):
            try:
                with open(self.seek_file, 'r') as f:
                    data = json.load(f)
                    self.position = data.get('position', 0)
                    logger.info(f"Loaded seek position: {self.position}")
            except Exception as e:
                logger.warning(f"Failed to load seek file: {e}. Starting from beginning.")
                self.position = 0
    
    def save_seek(self, position: int) -> None:
        """Save current position to seek file"""
        os.makedirs(os.path.dirname(self.seek_file), exist_ok=True)
        try:
            with open(self.seek_file, 'w') as f:
                json.dump({'position': position, 'timestamp': time.time()}, f)
        except Exception as e:
            logger.error(f"Failed to save seek position: {e}")


class LogShipper:
    """Main log shipper agent for forwarding Suricata events"""
    
    def __init__(self, config: ShipperConfig):
        self.config = config
        self.seek_tracker = SeekTracker(config.seek_file_path)
        self.session = self._create_session()
        self.current_batch = EventBatch(config)
        self.running = False
        self._last_ship_time = 0
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.retry_attempts,
            backoff_factor=self.config.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.brain_api_key}',
            'User-Agent': 'HungryHoundDog-LogShipper/1.0'
        })
        
        return session
    
    def read_events(self) -> List[Dict[str, Any]]:
        """Read new events from EVE log file"""
        events = []
        
        if not os.path.exists(self.config.eve_log_path):
            logger.warning(f"EVE log not found: {self.config.eve_log_path}")
            return events
        
        try:
            with open(self.config.eve_log_path, 'r') as f:
                # Seek to last known position
                f.seek(self.seek_tracker.position)
                
                # Read lines and parse JSON events
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON event: {e}")
                
                # Update seek position
                new_position = f.tell()
                self.seek_tracker.save_seek(new_position)
                
                if events:
                    logger.debug(f"Read {len(events)} new events from EVE log")
        
        except Exception as e:
            logger.error(f"Error reading EVE log: {e}")
        
        return events
    
    def ship_batch(self, batch: EventBatch) -> bool:
        """Ship batch to Brain server"""
        if not batch.events:
            logger.debug("Skipping empty batch")
            return True
        
        payload = batch.to_payload()
        
        try:
            logger.info(f"Shipping batch {batch.batch_id} with {len(batch.events)} events")
            
            response = self.session.post(
                self.config.brain_endpoint,
                json=payload,
                verify=self.config.verify_ssl,
                timeout=(self.config.connect_timeout, self.config.read_timeout)
            )
            
            response.raise_for_status()
            logger.info(f"Successfully shipped batch {batch.batch_id}")
            return True
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout shipping batch {batch.batch_id}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error shipping batch: {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error shipping batch: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error shipping batch: {e}")
            return False
    
    def process_events(self) -> None:
        """Process events and manage batching"""
        new_events = self.read_events()
        
        for event in new_events:
            self.current_batch.add_event(event)
            
            # Ship batch if full
            if self.current_batch.is_full():
                self.ship_batch(self.current_batch)
                self.current_batch = EventBatch(self.config)
        
        # Periodically ship stale batches
        current_time = time.time()
        if (current_time - self._last_ship_time) >= self.config.ship_interval:
            if self.current_batch.events:
                self.ship_batch(self.current_batch)
                self.current_batch = EventBatch(self.config)
            self._last_ship_time = current_time
    
    def run(self) -> None:
        """Main event loop"""
        self.running = True
        logger.info("Log Shipper started")
        
        try:
            while self.running:
                self.process_events()
                time.sleep(5)  # Process events every 5 seconds
        
        except KeyboardInterrupt:
            logger.info("Log Shipper interrupted by user")
        except Exception as e:
            logger.critical(f"Unexpected error in main loop: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Clean shutdown"""
        logger.info("Shutting down Log Shipper")
        
        # Try to ship remaining events
        if self.current_batch.events:
            logger.info("Shipping remaining events before shutdown")
            self.ship_batch(self.current_batch)
        
        self.session.close()
        self.running = False


def main():
    """Main entry point"""
    config_file = os.environ.get('SHIPPER_CONFIG', '/etc/hungryhounddog/agent/config.yaml')
    
    if not os.path.exists(config_file):
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    try:
        config = ShipperConfig.from_yaml(config_file)
        shipper = LogShipper(config)
        shipper.run()
    except Exception as e:
        logger.critical(f"Failed to start Log Shipper: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
