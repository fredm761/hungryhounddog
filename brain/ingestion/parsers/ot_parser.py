"""
OT Protocol Parser
==================
Extracts and enriches OT-specific protocol fields from Suricata events.
Handles Modbus, MQTT, OPC UA, DNP3, and other industrial protocols.

Author: HungryHoundDog Team
"""

import logging
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)


def enrich_ot_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich event with OT-specific protocol extraction.
    
    Args:
        event: Parsed event dictionary
        
    Returns:
        Enriched event dictionary with OT protocol fields
    """
    try:
        raw_data = event.get("raw_data", {})
        
        # Detect and parse OT protocols
        event["ot_data"] = {
            "modbus": _parse_modbus(raw_data),
            "mqtt": _parse_mqtt(raw_data),
            "opcua": _parse_opcua(raw_data),
            "dnp3": _parse_dnp3(raw_data),
            "profibus": _parse_profibus(raw_data)
        }
        
        return event
        
    except Exception as e:
        logger.error(f"OT enrichment error: {str(e)}", exc_info=True)
        return event


def _parse_modbus(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract Modbus protocol information.
    
    Returns fields like function code, register address, register count.
    """
    modbus_data = {}
    
    try:
        payload = raw_event.get("app_layer", {}).get("payload", "")
        if not payload:
            return modbus_data
        
        # Extract from hex payload (simplified parsing)
        # Modbus frame structure: [Unit ID][Function Code][Address][Count/Data]
        if len(payload) >= 4:
            # Function code at offset 1
            function_code = int(payload[2:4], 16) if payload[2:4] else None
            
            # Register address (big-endian) at offset 2
            register_addr = int(payload[4:8], 16) if payload[4:8] else None
            
            # Quantity at offset 4
            quantity = int(payload[8:12], 16) if payload[8:12] else None
            
            modbus_data = {
                "function_code": function_code,
                "function_name": _get_modbus_function_name(function_code),
                "register_address": register_addr,
                "quantity": quantity,
                "detected": True
            }
    except Exception as e:
        logger.debug(f"Modbus parsing error: {str(e)}")
    
    return modbus_data


def _get_modbus_function_name(function_code: int) -> str:
    """Map Modbus function codes to human-readable names."""
    modbus_functions = {
        1: "Read Coils",
        2: "Read Discrete Inputs",
        3: "Read Holding Registers",
        4: "Read Input Registers",
        5: "Write Single Coil",
        6: "Write Single Register",
        15: "Write Multiple Coils",
        16: "Write Multiple Registers",
        23: "Read Write Multiple Registers"
    }
    return modbus_functions.get(function_code, f"Function {function_code}")


def _parse_mqtt(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract MQTT protocol information.
    
    Returns fields like topic, payload, QoS, retained flag.
    """
    mqtt_data = {}
    
    try:
        http_data = raw_event.get("http", {})
        if not http_data:
            return mqtt_data
        
        # Check if MQTT (port 1883 or 8883)
        dest_port = raw_event.get("dest_port")
        if dest_port in [1883, 8883]:
            uri = http_data.get("uri", "")
            hostname = http_data.get("hostname", "")
            
            # Extract topic from URI or hostname
            mqtt_data = {
                "topic": uri,
                "broker": hostname,
                "port": dest_port,
                "tls": dest_port == 8883,
                "detected": True
            }
    except Exception as e:
        logger.debug(f"MQTT parsing error: {str(e)}")
    
    return mqtt_data


def _parse_opcua(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract OPC UA protocol information.
    
    Returns fields like namespace, node ID, service type.
    """
    opcua_data = {}
    
    try:
        # OPC UA typically runs on port 4840
        dest_port = raw_event.get("dest_port")
        if dest_port == 4840:
            http_data = raw_event.get("http", {})
            
            opcua_data = {
                "endpoint": http_data.get("uri", ""),
                "service": _extract_opcua_service(http_data.get("uri", "")),
                "port": dest_port,
                "detected": True
            }
    except Exception as e:
        logger.debug(f"OPC UA parsing error: {str(e)}")
    
    return opcua_data


def _extract_opcua_service(uri: str) -> str:
    """Extract OPC UA service type from URI."""
    services = {
        "discovery": "GetEndpoints",
        "create_session": "CreateSession",
        "read": "Read",
        "write": "Write",
        "browse": "Browse",
        "call": "Call"
    }
    
    for key, service in services.items():
        if key.lower() in uri.lower():
            return service
    
    return "Unknown"


def _parse_dnp3(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract DNP3 protocol information.
    
    Returns fields like function code, object class.
    """
    dnp3_data = {}
    
    try:
        # DNP3 typically runs on port 20000
        dest_port = raw_event.get("dest_port")
        if dest_port == 20000:
            payload = raw_event.get("app_layer", {}).get("payload", "")
            
            if payload and len(payload) >= 8:
                # DNP3 ASDU fields extraction
                function_code = int(payload[6:8], 16) if payload[6:8] else None
                
                dnp3_data = {
                    "function_code": function_code,
                    "function_name": _get_dnp3_function_name(function_code),
                    "port": dest_port,
                    "detected": True
                }
    except Exception as e:
        logger.debug(f"DNP3 parsing error: {str(e)}")
    
    return dnp3_data


def _get_dnp3_function_name(function_code: int) -> str:
    """Map DNP3 function codes to names."""
    dnp3_functions = {
        0: "Confirm",
        1: "Read",
        2: "Write",
        3: "Select",
        4: "Operate",
        5: "Direct Operate",
        6: "Direct Operate NoAck",
        7: "Imm. Freeze",
        8: "Imm. Freeze NoAck",
        9: "Freeze & Clear",
        10: "Freeze & Clear NoAck",
        11: "Freeze w/ Time",
        12: "Freeze w/ Time NoAck",
        129: "Response",
        130: "Unsolicited Response",
        131: "Authenticate"
    }
    return dnp3_functions.get(function_code, f"Function {function_code}")


def _parse_profibus(raw_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract PROFIBUS protocol information.
    
    Returns fields like slave address, function code.
    """
    profibus_data = {}
    
    try:
        payload = raw_event.get("app_layer", {}).get("payload", "")
        if not payload or len(payload) < 4:
            return profibus_data
        
        # PROFIBUS frame structure (simplified)
        # [Start][Length][PDU]
        slave_addr = int(payload[2:4], 16) if payload[2:4] else None
        
        profibus_data = {
            "slave_address": slave_addr,
            "detected": True
        }
    except Exception as e:
        logger.debug(f"PROFIBUS parsing error: {str(e)}")
    
    return profibus_data


def is_ot_traffic(event: Dict[str, Any]) -> bool:
    """
    Determine if event represents OT protocol traffic.
    
    Args:
        event: Event dictionary
        
    Returns:
        True if OT protocol detected
    """
    ot_data = event.get("ot_data", {})
    
    # Check if any OT protocol was detected
    for protocol, data in ot_data.items():
        if isinstance(data, dict) and data.get("detected"):
            return True
    
    return False


def get_ot_severity(event: Dict[str, Any]) -> str:
    """
    Determine severity for OT-specific threat patterns.
    
    Args:
        event: Event dictionary with OT data
        
    Returns:
        Severity level: "critical", "high", "medium", "low"
    """
    ot_data = event.get("ot_data", {})
    severity = "low"
    
    # Check for suspicious OT patterns
    modbus = ot_data.get("modbus", {})
    if modbus.get("function_code") in [5, 6, 15, 16]:  # Write operations
        severity = "high"
    
    dnp3 = ot_data.get("dnp3", {})
    if dnp3.get("function_code") in [2, 3, 4, 5]:  # Control operations
        severity = "high"
    
    # Check for large data transfers
    bytes_transferred = event.get("bytes_out", 0) + event.get("bytes_in", 0)
    if bytes_transferred > 10000:
        severity = "medium"
    
    return severity
