#!/usr/bin/env python3
"""
02_modbus_read.py: Legitimate Modbus read baseline traffic.

Performs authorized Modbus TCP reads from a simulated PLC/RTU to establish
baseline traffic patterns and provide legitimate telemetry.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModbusBaselineReader:
    """Performs legitimate Modbus register reads for baseline traffic."""

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 502,
        unit_id: int = 1
    ):
        """
        Initialize Modbus client.

        Args:
            host: Target PLC/RTU IP address.
            port: Modbus TCP port (default 502).
            unit_id: Modbus unit identifier.
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.client = ModbusTcpClient(host=host, port=port, timeout=10)
        self.readings = []

    def connect(self) -> bool:
        """
        Establish connection to Modbus server.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            if self.client.connect():
                logger.info(f"Connected to Modbus server at {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Failed to connect to {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def read_holding_registers(
        self,
        start_address: int = 0,
        quantity: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Read holding registers from PLC.

        Args:
            start_address: Starting register address.
            quantity: Number of registers to read.

        Returns:
            Dictionary with register values or None on failure.
        """
        try:
            result = self.client.read_holding_registers(
                address=start_address,
                count=quantity,
                slave=self.unit_id
            )

            if not result.isError():
                register_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "holding_registers",
                    "start_address": start_address,
                    "quantity": quantity,
                    "values": result.registers
                }
                logger.info(f"Read {quantity} holding registers from {start_address}")
                self.readings.append(register_data)
                return register_data
            else:
                logger.warning(f"Modbus error reading registers: {result}")
                return None

        except ModbusException as e:
            logger.error(f"Modbus exception: {str(e)}")
            return None

    def read_coils(
        self,
        start_address: int = 0,
        quantity: int = 8
    ) -> Optional[Dict[str, Any]]:
        """
        Read coils (digital outputs) from PLC.

        Args:
            start_address: Starting coil address.
            quantity: Number of coils to read.

        Returns:
            Dictionary with coil values or None on failure.
        """
        try:
            result = self.client.read_coils(
                address=start_address,
                count=quantity,
                slave=self.unit_id
            )

            if not result.isError():
                coil_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": "coils",
                    "start_address": start_address,
                    "quantity": quantity,
                    "values": result.bits
                }
                logger.info(f"Read {quantity} coils from {start_address}")
                self.readings.append(coil_data)
                return coil_data
            else:
                logger.warning(f"Modbus error reading coils: {result}")
                return None

        except ModbusException as e:
            logger.error(f"Modbus exception: {str(e)}")
            return None

    def continuous_read(
        self,
        interval: int = 5,
        duration: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform continuous reads at regular intervals.

        Args:
            interval: Seconds between reads.
            duration: Total duration in seconds (None for infinite).

        Returns:
            List of all readings collected.
        """
        elapsed = 0
        try:
            while duration is None or elapsed < duration:
                logger.info(f"Collecting baseline reading {len(self.readings) + 1}")

                self.read_holding_registers(start_address=0, quantity=10)
                self.read_coils(start_address=0, quantity=8)

                if duration is not None:
                    elapsed += interval

                time.sleep(interval)

            logger.info(f"Continuous read complete: {len(self.readings)} readings collected")
            return self.readings

        except KeyboardInterrupt:
            logger.info("Read interrupted by user")
            return self.readings

    def disconnect(self) -> None:
        """Close Modbus connection."""
        self.client.close()
        logger.info("Disconnected from Modbus server")

    def export_readings(self, filepath: str) -> None:
        """
        Export readings to JSON file.

        Args:
            filepath: Output JSON file path.
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.readings, f, indent=2)
            logger.info(f"Readings exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")


def main() -> int:
    """Execute legitimate Modbus reads."""
    reader = ModbusBaselineReader(host="192.168.1.100")

    if not reader.connect():
        return 1

    try:
        # Perform 10 reads at 5-second intervals
        readings = reader.continuous_read(interval=5, duration=50)
        reader.export_readings("/tmp/modbus_baseline.json")

        print(f"Collected {len(readings)} baseline readings")
        print(json.dumps(readings[-1], indent=2))
        return 0

    finally:
        reader.disconnect()


if __name__ == "__main__":
    sys.exit(main())
