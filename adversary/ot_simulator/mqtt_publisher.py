#!/usr/bin/env python3
"""
mqtt_publisher.py: Simulated OT telemetry publisher via MQTT.

Publishes realistic OT system metrics (temperature, pressure, flow rate)
to Mosquitto broker at regular intervals.
"""

import json
import logging
import random
import sys
import time
from datetime import datetime
from typing import Dict, Any

import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OTTelemetryPublisher:
    """Publishes simulated OT telemetry via MQTT."""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        device_id: str = "plc-01"
    ):
        """
        Initialize MQTT publisher.

        Args:
            broker_host: MQTT broker hostname.
            broker_port: MQTT broker port.
            device_id: Device identifier.
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.device_id = device_id
        self.client = mqtt.Client(client_id=device_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        # Telemetry state
        self.temperature = 25.0
        self.pressure = 150.0
        self.flow_rate = 45.0
        self.messages_published = 0

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Dict, rc: int) -> None:
        """Handle connection event."""
        if rc == 0:
            logger.info(f"Connected to MQTT broker {self.broker_host}:{self.broker_port}")
        else:
            logger.error(f"Connection failed with code {rc}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Handle disconnection event."""
        logger.info(f"Disconnected from MQTT broker (code {rc})")

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int) -> None:
        """Handle publish confirmation."""
        self.messages_published += 1

    def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            time.sleep(1)  # Give connection time to establish
            return True
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def generate_telemetry(self) -> Dict[str, Any]:
        """
        Generate realistic OT telemetry with slight variations.

        Returns:
            Dictionary with telemetry data.
        """
        # Add realistic sensor noise
        self.temperature += random.uniform(-0.5, 0.5)
        self.pressure += random.uniform(-2.0, 2.0)
        self.flow_rate += random.uniform(-1.0, 1.0)

        # Clamp values to realistic ranges
        self.temperature = max(15.0, min(40.0, self.temperature))
        self.pressure = max(80.0, min(200.0, self.pressure))
        self.flow_rate = max(30.0, min(60.0, self.flow_rate))

        telemetry = {
            "timestamp": datetime.utcnow().isoformat(),
            "device_id": self.device_id,
            "temperature_celsius": round(self.temperature, 2),
            "pressure_bar": round(self.pressure, 1),
            "flow_rate_lpm": round(self.flow_rate, 1),
            "system_status": "normal"
        }

        return telemetry

    def publish_telemetry(self) -> None:
        """Publish telemetry to MQTT topics."""
        telemetry = self.generate_telemetry()

        # Publish to topic hierarchy
        topics = [
            f"ot/{self.device_id}/temperature",
            f"ot/{self.device_id}/pressure",
            f"ot/{self.device_id}/flow_rate",
            f"ot/{self.device_id}/telemetry"
        ]

        payloads = [
            json.dumps({"value": telemetry["temperature_celsius"], "unit": "C"}),
            json.dumps({"value": telemetry["pressure_bar"], "unit": "bar"}),
            json.dumps({"value": telemetry["flow_rate_lpm"], "unit": "L/min"}),
            json.dumps(telemetry)
        ]

        for topic, payload in zip(topics, payloads):
            try:
                self.client.publish(topic, payload, qos=1)
                logger.debug(f"Published to {topic}")
            except Exception as e:
                logger.error(f"Publish failed: {str(e)}")

    def publish_continuous(
        self,
        interval: int = 5,
        duration: int = 300
    ) -> int:
        """
        Publish telemetry continuously.

        Args:
            interval: Seconds between publishes.
            duration: Total duration in seconds.

        Returns:
            Total messages published.
        """
        logger.info(f"Publishing telemetry every {interval}s for {duration}s")

        elapsed = 0
        try:
            while elapsed < duration:
                self.publish_telemetry()
                logger.info(
                    f"Published #{self.messages_published}: "
                    f"T={self.temperature:.1f}C, P={self.pressure:.1f}bar, F={self.flow_rate:.1f}L/min"
                )

                elapsed += interval
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Publishing interrupted")

        logger.info(f"Publishing complete: {self.messages_published} messages sent")
        return self.messages_published

    def disconnect(self) -> None:
        """Disconnect from broker."""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("Disconnected from MQTT broker")


def main() -> int:
    """Publish OT telemetry via MQTT."""
    try:
        publisher = OTTelemetryPublisher(
            broker_host="localhost",
            broker_port=1883,
            device_id="plc-01"
        )

        if not publisher.connect():
            return 1

        try:
            # Publish for 5 minutes at 5-second intervals
            published = publisher.publish_continuous(interval=5, duration=300)
            print(f"Successfully published {published} messages")
            return 0

        finally:
            publisher.disconnect()

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
