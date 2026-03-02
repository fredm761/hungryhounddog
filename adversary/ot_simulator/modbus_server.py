#!/usr/bin/env python3
"""
modbus_server.py: Simulated PLC/RTU Modbus TCP server.

Implements a pymodbus TCP server with configurable holding registers,
coils, and discrete inputs to simulate OT device behavior.
"""

import json
import logging
import sys
import time
from typing import Dict, List, Any

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer
from pymodbus.device import ModbusDeviceIdentification, ModbusBasicQuery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OTSimulator:
    """Simulated PLC/RTU with Modbus TCP interface."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 502,
        device_name: str = "Simulated PLC"
    ):
        """
        Initialize OT simulator.

        Args:
            host: Server bind address.
            port: Modbus TCP port.
            device_name: Device identifier.
        """
        self.host = host
        self.port = port
        self.device_name = device_name
        self.context = None

    def create_datastore(self) -> ModbusServerContext:
        """
        Create Modbus datastore with initial values.

        Returns:
            Configured ModbusServerContext.
        """
        logger.info("Initializing Modbus datastore...")

        # Create holding registers (0-99: normal operation, 100+: system state)
        holding_registers = ModbusSequentialDataBlock(0, [
            # Temperature sensors (register 0-4)
            2500,  # Reactor temp (25.00 C)
            3200,  # Inlet temp (32.00 C)
            1800,  # Outlet temp (18.00 C)
            2400,  # Ambient temp (24.00 C)
            0,
            # Pressure sensors (register 5-9)
            1500,  # System pressure (150.0 bar)
            800,   # Tank pressure (80.0 bar)
            1200,  # Line pressure (120.0 bar)
            900,   # Backup pressure (90.0 bar)
            0,
            # Flow rates (register 10-14)
            450,   # Primary pump flow (45.0 L/min)
            280,   # Secondary pump flow (28.0 L/min)
            150,   # Bypass flow (15.0 L/min)
            100,   # Drain flow (10.0 L/min)
            0,
            # Alarm thresholds (register 15-19)
            3500,  # High temp alarm (35.00 C)
            2000,  # Low temp alarm (20.00 C)
            2000,  # High pressure alarm (200.0 bar)
            500,   # Low pressure alarm (50.0 bar)
            0,
            # System setpoints (register 20-29)
            2500,  # Target temperature
            1500,  # Target pressure
            400,   # Target flow rate
            0, 0, 0, 0, 0, 0, 0
        ] + [0] * 70)

        # Create coils (digital outputs)
        coils = ModbusSequentialDataBlock(0, [
            True,   # Pump 1 enabled
            True,   # Pump 2 enabled
            False,  # Pump 3 enabled
            True,   # Heater enabled
            False,  # Cooler enabled
            True,   # Safety interlock 1
            True,   # Safety interlock 2
            False   # Emergency shutdown
        ] + [False] * 120)

        # Create discrete inputs (sensor status)
        discrete_inputs = ModbusSequentialDataBlock(0, [
            True,   # Temp sensor 1 OK
            True,   # Temp sensor 2 OK
            True,   # Pressure sensor OK
            True,   # Flow sensor OK
            True,   # Motor 1 running
            True,   # Motor 2 running
            False,  # Motor 3 running
            False   # Alarm active
        ] + [False] * 120)

        # Create input registers (read-only analog inputs)
        input_registers = ModbusSequentialDataBlock(0, [
            2500,  # Reactor temp (read-only)
            1500,  # System pressure (read-only)
            450,   # Primary flow rate (read-only)
            42,    # System status code
            0, 0, 0, 0, 0, 0
        ] + [0] * 90)

        # Create slave context
        slave_context = ModbusSlaveContext(
            di=discrete_inputs,
            co=coils,
            hr=holding_registers,
            ir=input_registers
        )

        # Create server context
        context = ModbusServerContext({0x00: slave_context}, single=False)
        logger.info("Modbus datastore initialized")

        return context

    def setup_device_info(self) -> ModbusDeviceIdentification:
        """
        Setup Modbus device identification.

        Returns:
            ModbusDeviceIdentification object.
        """
        identity = ModbusDeviceIdentification(
            info_name=self.device_name,
            info={
                0x00: "Simulated PLC/RTU",
                0x01: "HungryHoundDog OT Lab",
                0x02: "1.0.0",
                0x03: "Modbus TCP Server",
                0x04: "OT Simulation",
                0x05: "Test Lab"
            }
        )
        logger.info(f"Device info: {self.device_name}")
        return identity

    def start_server(self) -> None:
        """Start Modbus TCP server."""
        try:
            self.context = self.create_datastore()
            identity = self.setup_device_info()

            logger.info(f"Starting Modbus TCP server on {self.host}:{self.port}")

            StartAsyncTcpServer(
                context=self.context,
                identity=identity,
                address=(self.host, self.port)
            )

            logger.info(f"Modbus server running on {self.host}:{self.port}")

            # Keep server running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Server shutdown requested")

        except Exception as e:
            logger.error(f"Server error: {str(e)}")
            raise


def main() -> int:
    """Start Modbus server."""
    try:
        simulator = OTSimulator(host="0.0.0.0", port=502, device_name="Lab PLC")
        simulator.start_server()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
