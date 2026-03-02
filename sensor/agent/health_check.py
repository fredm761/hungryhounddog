#!/usr/bin/env python3
"""
HungryHoundDog Health Check Agent

Monitors Raspberry Pi 4 sensor health metrics including CPU usage, RAM,
disk space, Suricata process status, and network interface status.
Reports metrics as JSON to the Brain server's health endpoint.

This agent provides real-time visibility into sensor node performance
and availability for the central management system.
"""

import json
import os
import sys
import time
import logging
import psutil
import socket
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import yaml
import subprocess

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. Install with: pip install requests pyyaml psutil")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/hungryhounddog/health_check.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class HealthConfig:
    """Configuration for health check agent"""
    brain_endpoint: str
    brain_api_key: str
    health_check_interval: int
    sensor_id: str
    sensor_name: str
    suricata_process_name: str
    network_interfaces: list
    verify_ssl: bool
    connect_timeout: int
    read_timeout: int

    @staticmethod
    def from_yaml(config_file: str) -> 'HealthConfig':
        """Load configuration from YAML file"""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        agent_config = config_data.get('agent', {})
        return HealthConfig(
            brain_endpoint=agent_config.get('brain_health_endpoint', 'https://brain.hungryhounddog.local/api/health'),
            brain_api_key=agent_config.get('brain_api_key', ''),
            health_check_interval=agent_config.get('health_check_interval', 60),
            sensor_id=agent_config.get('sensor_id', 'sensor-001'),
            sensor_name=agent_config.get('sensor_name', 'RPi4-Sensor-01'),
            suricata_process_name=agent_config.get('suricata_process_name', 'suricata'),
            network_interfaces=agent_config.get('network_interfaces', ['eth0', 'wlan0']),
            verify_ssl=agent_config.get('verify_ssl', True),
            connect_timeout=agent_config.get('connect_timeout', 10),
            read_timeout=agent_config.get('read_timeout', 30)
        )


class CPUMetrics:
    """CPU usage metrics"""
    
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Get CPU metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_freq = psutil.cpu_freq()
            
            # Per-core CPU usage
            per_core = psutil.cpu_percent(interval=1, percpu=True)
            
            return {
                'usage_percent': cpu_percent,
                'count_physical': cpu_count_physical,
                'count_logical': cpu_count_logical,
                'frequency_mhz': cpu_freq.current if cpu_freq else None,
                'per_core_usage': per_core,
                'load_average': os.getloadavg()
            }
        except Exception as e:
            logger.error(f"Error getting CPU metrics: {e}")
            return {'error': str(e)}


class MemoryMetrics:
    """Memory (RAM) usage metrics"""
    
    @staticmethod
    def get_metrics() -> Dict[str, Any]:
        """Get memory metrics"""
        try:
            virtual_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()
            
            return {
                'total_mb': virtual_memory.total / (1024 * 1024),
                'available_mb': virtual_memory.available / (1024 * 1024),
                'used_mb': virtual_memory.used / (1024 * 1024),
                'percent_used': virtual_memory.percent,
                'swap_total_mb': swap_memory.total / (1024 * 1024),
                'swap_used_mb': swap_memory.used / (1024 * 1024),
                'swap_percent_used': swap_memory.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory metrics: {e}")
            return {'error': str(e)}


class DiskMetrics:
    """Disk space metrics"""
    
    @staticmethod
    def get_metrics(root_path: str = '/') -> Dict[str, Any]:
        """Get disk metrics"""
        try:
            disk_usage = psutil.disk_usage(root_path)
            
            return {
                'path': root_path,
                'total_gb': disk_usage.total / (1024 ** 3),
                'used_gb': disk_usage.used / (1024 ** 3),
                'free_gb': disk_usage.free / (1024 ** 3),
                'percent_used': disk_usage.percent
            }
        except Exception as e:
            logger.error(f"Error getting disk metrics: {e}")
            return {'error': str(e)}


class ProcessMetrics:
    """Process-specific metrics for Suricata"""
    
    @staticmethod
    def is_running(process_name: str) -> bool:
        """Check if process is running"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == process_name:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking process status: {e}")
            return False
    
    @staticmethod
    def get_metrics(process_name: str) -> Dict[str, Any]:
        """Get process-specific metrics"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_num']):
                if proc.info['name'] == process_name:
                    mem_info = proc.memory_info()
                    return {
                        'running': True,
                        'pid': proc.info['pid'],
                        'memory_mb': mem_info.rss / (1024 * 1024),
                        'cpu_core': proc.info['cpu_num'],
                        'status': proc.status()
                    }
            
            return {
                'running': False,
                'pid': None,
                'memory_mb': 0,
                'cpu_core': None,
                'status': 'not_running'
            }
        except Exception as e:
            logger.error(f"Error getting process metrics: {e}")
            return {'error': str(e)}


class NetworkMetrics:
    """Network interface metrics"""
    
    @staticmethod
    def get_interface_metrics(interface: str) -> Dict[str, Any]:
        """Get metrics for a specific network interface"""
        try:
            # Check if interface exists
            if interface not in psutil.net_if_addrs():
                return {
                    'interface': interface,
                    'status': 'down',
                    'error': 'Interface not found'
                }
            
            # Get interface stats
            if_stats = psutil.net_if_stats()[interface] if interface in psutil.net_if_stats() else None
            
            # Get addresses
            if_addrs = psutil.net_if_addrs().get(interface, [])
            addresses = {}
            for addr in if_addrs:
                addresses[addr.family.name] = addr.address
            
            status = 'up' if if_stats.isup else 'down'
            
            return {
                'interface': interface,
                'status': status,
                'is_up': if_stats.isup if if_stats else False,
                'mtu': if_stats.mtu if if_stats else None,
                'speed_mbps': if_stats.speed if if_stats else None,
                'addresses': addresses,
                'packets_sent': if_stats.packets_sent if if_stats else 0,
                'packets_recv': if_stats.packets_recv if if_stats else 0,
                'bytes_sent': if_stats.bytes_sent if if_stats else 0,
                'bytes_recv': if_stats.bytes_recv if if_stats else 0,
                'errors_in': if_stats.errin if if_stats else 0,
                'errors_out': if_stats.errout if if_stats else 0,
                'drop_in': if_stats.dropin if if_stats else 0,
                'drop_out': if_stats.dropout if if_stats else 0
            }
        except Exception as e:
            logger.error(f"Error getting network metrics for {interface}: {e}")
            return {'interface': interface, 'error': str(e)}
    
    @staticmethod
    def get_all_metrics(interfaces: list) -> Dict[str, Any]:
        """Get metrics for all configured interfaces"""
        return {
            interface: NetworkMetrics.get_interface_metrics(interface)
            for interface in interfaces
        }


class HealthCheckAgent:
    """Main health check agent"""
    
    def __init__(self, config: HealthConfig):
        self.config = config
        self.session = self._create_session()
        self.running = False
    
    def _create_session(self) -> requests.Session:
        """Create requests session"""
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.brain_api_key}',
            'User-Agent': 'HungryHoundDog-HealthCheck/1.0'
        })
        return session
    
    def collect_health_metrics(self) -> Dict[str, Any]:
        """Collect all health metrics"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'sensor_id': self.config.sensor_id,
            'sensor_name': self.config.sensor_name,
            'hostname': socket.gethostname(),
            'cpu': CPUMetrics.get_metrics(),
            'memory': MemoryMetrics.get_metrics(),
            'disk': DiskMetrics.get_metrics(),
            'suricata': ProcessMetrics.get_metrics(self.config.suricata_process_name),
            'network': NetworkMetrics.get_all_metrics(self.config.network_interfaces)
        }
    
    def report_health(self, metrics: Dict[str, Any]) -> bool:
        """Report health metrics to Brain server"""
        try:
            logger.debug(f"Reporting health metrics to {self.config.brain_endpoint}")
            
            response = self.session.post(
                self.config.brain_endpoint,
                json=metrics,
                verify=self.config.verify_ssl,
                timeout=(self.config.connect_timeout, self.config.read_timeout)
            )
            
            response.raise_for_status()
            logger.info("Successfully reported health metrics")
            return True
        
        except requests.exceptions.Timeout:
            logger.error("Timeout reporting health metrics")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error reporting health: {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error reporting health: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error reporting health: {e}")
            return False
    
    def run(self) -> None:
        """Main event loop"""
        self.running = True
        logger.info("Health Check Agent started")
        
        try:
            while self.running:
                metrics = self.collect_health_metrics()
                self.report_health(metrics)
                time.sleep(self.config.health_check_interval)
        
        except KeyboardInterrupt:
            logger.info("Health Check Agent interrupted by user")
        except Exception as e:
            logger.critical(f"Unexpected error in main loop: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Clean shutdown"""
        logger.info("Shutting down Health Check Agent")
        self.session.close()
        self.running = False


def main():
    """Main entry point"""
    config_file = os.environ.get('HEALTH_CONFIG', '/etc/hungryhounddog/agent/config.yaml')
    
    if not os.path.exists(config_file):
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    try:
        config = HealthConfig.from_yaml(config_file)
        agent = HealthCheckAgent(config)
        agent.run()
    except Exception as e:
        logger.critical(f"Failed to start Health Check Agent: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
