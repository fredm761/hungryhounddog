#!/usr/bin/env python3
"""
baseline_traffic.py: Normal OT network traffic generator.

Generates realistic baseline traffic including periodic Modbus reads,
MQTT publishes, DNS queries, and HTTP health checks.
"""

import json
import logging
import random
import sys
import time
from datetime import datetime
from typing import Dict, Any

from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BaselineTrafficGenerator:
    """Generates normal-looking OT network traffic patterns."""

    def __init__(self):
        """Initialize traffic generator."""
        self.traffic_log = []
        self.modbus_client = ModbusTcpClient(host="192.168.1.100", port=502, timeout=5)
        self.mqtt_client = mqtt.Client(client_id="baseline-gen")
        self.mqtt_client.connect("localhost", 1883, keepalive=60)
        self.mqtt_client.loop_start()

    def log_traffic_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log traffic event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "details": details
        }
        self.traffic_log.append(event)
        logger.info(f"Traffic: {event_type} - {details}")

    def generate_modbus_reads(self) -> None:
        """Generate legitimate Modbus read traffic."""
        try:
            if self.modbus_client.connect():
                # Read temperature registers
                result = self.modbus_client.read_holding_registers(0, 5, slave=1)
                if not result.isError():
                    self.log_traffic_event("modbus_read", {
                        "type": "holding_registers",
                        "address": 0,
                        "count": 5,
                        "success": True
                    })

                # Read pressure registers
                result = self.modbus_client.read_holding_registers(5, 5, slave=1)
                if not result.isError():
                    self.log_traffic_event("modbus_read", {
                        "type": "holding_registers",
                        "address": 5,
                        "count": 5,
                        "success": True
                    })

                # Read status coils
                result = self.modbus_client.read_coils(0, 8, slave=1)
                if not result.isError():
                    self.log_traffic_event("modbus_read", {
                        "type": "coils",
                        "address": 0,
                        "count": 8,
                        "success": True
                    })

                self.modbus_client.close()
            else:
                logger.warning("Could not connect to Modbus server")

        except Exception as e:
            logger.debug(f"Modbus error: {str(e)}")

    def generate_mqtt_publishes(self) -> None:
        """Generate MQTT telemetry publishes."""
        try:
            devices = ["plc-01", "plc-02", "sensor-01"]
            for device in devices:
                telemetry = {
                    "device": device,
                    "temperature": round(20 + random.uniform(-5, 5), 2),
                    "pressure": round(150 + random.uniform(-20, 20), 1),
                    "flow_rate": round(45 + random.uniform(-10, 10), 1)
                }

                topic = f"ot/{device}/telemetry"
                self.mqtt_client.publish(topic, json.dumps(telemetry), qos=1)

                self.log_traffic_event("mqtt_publish", {
                    "device": device,
                    "topic": topic,
                    "success": True
                })

        except Exception as e:
            logger.debug(f"MQTT error: {str(e)}")

    def generate_dns_queries(self) -> None:
        """Log simulated DNS queries."""
        domains = [
            "ntp.ubuntu.com",
            "time.google.com",
            "8.8.8.8",
            "logger.internal"
        ]

        for domain in domains:
            self.log_traffic_event("dns_query", {
                "query": domain,
                "query_type": "A",
                "response_code": "NOERROR",
                "success": True
            })

    def generate_http_health_checks(self) -> None:
        """Log simulated HTTP health checks."""
        endpoints = [
            "http://192.168.1.1/api/health",
            "http://192.168.1.20/status",
            "http://logger.internal:5000/health"
        ]

        for endpoint in endpoints:
            self.log_traffic_event("http_get", {
                "endpoint": endpoint,
                "method": "GET",
                "status_code": 200,
                "response_time_ms": random.randint(50, 200),
                "success": True
            })

    def generate_baseline_cycle(self) -> None:
        """Generate one cycle of baseline traffic."""
        logger.info("=== Generating baseline traffic cycle ===")

        self.generate_modbus_reads()
        time.sleep(2)

        self.generate_mqtt_publishes()
        time.sleep(2)

        self.generate_dns_queries()
        time.sleep(1)

        self.generate_http_health_checks()

    def run_continuous(self, interval: int = 30, duration: int = 600) -> None:
        """
        Run continuous baseline traffic generation.

        Args:
            interval: Seconds between cycles.
            duration: Total duration in seconds.
        """
        logger.info(f"Starting baseline traffic generation ({duration}s, cycle every {interval}s)")

        elapsed = 0
        try:
            while elapsed < duration:
                self.generate_baseline_cycle()
                logger.info(f"Total traffic events: {len(self.traffic_log)}")

                elapsed += interval
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Traffic generation interrupted")

        logger.info(f"Traffic generation complete: {len(self.traffic_log)} events")

    def export_log(self, filepath: str) -> None:
        """Export traffic log to JSON."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.traffic_log, f, indent=2)
            logger.info(f"Traffic log exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")

    def shutdown(self) -> None:
        """Clean up resources."""
        self.mqtt_client.loop_stop()
        logger.info("Traffic generator shutdown")


def main() -> int:
    """Generate baseline OT network traffic."""
    generator = BaselineTrafficGenerator()

    try:
        # Generate traffic for 10 minutes
        generator.run_continuous(interval=30, duration=600)
        generator.export_log("/tmp/baseline_traffic.json")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1

    finally:
        generator.shutdown()


if __name__ == "__main__":
    sys.exit(main())
