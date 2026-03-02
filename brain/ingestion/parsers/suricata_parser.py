"""
Suricata EVE JSON Parser
========================
Normalizes Suricata EVE JSON events into standardized internal format.
Handles alert, flow, dns, http, and tls event types.

Author: HungryHoundDog Team
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


def parse_event(raw_event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse raw Suricata EVE JSON event and normalize it.
    
    Args:
        raw_event: Raw event dictionary from Suricata
        
    Returns:
        List of normalized event dictionaries
    """
    try:
        event_type = raw_event.get("event_type", "unknown")
        
        if event_type == "alert":
            return [_parse_alert(raw_event)]
        elif event_type == "flow":
            return [_parse_flow(raw_event)]
        elif event_type == "dns":
            return [_parse_dns(raw_event)]
        elif event_type == "http":
            return [_parse_http(raw_event)]
        elif event_type == "tls":
            return [_parse_tls(raw_event)]
        else:
            return [_parse_generic(raw_event)]
            
    except Exception as e:
        logger.error(f"Error parsing event: {str(e)}", exc_info=True)
        return []


def _parse_alert(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Suricata alert event.
    
    Alert events contain IDS/IPS detections with signature and severity info.
    """
    timestamp_str = event.get("timestamp", "")
    
    parsed = {
        "timestamp": _parse_timestamp(timestamp_str),
        "event_type": "alert",
        "flow_id": event.get("flow_id"),
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dst_ip": event.get("dest_ip"),
        "dst_port": event.get("dest_port"),
        "protocol": event.get("proto"),
        "tags": event.get("alert", {}).get("category", "").split(",") if event.get("alert") else [],
        "raw_data": event
    }
    
    # Extract alert-specific fields
    alert_data = event.get("alert", {})
    if alert_data:
        parsed.update({
            "alert_message": alert_data.get("signature", ""),
            "signature_id": alert_data.get("signature_id"),
            "severity": alert_data.get("severity", 0),
            "category": alert_data.get("category", "")
        })
    
    return parsed


def _parse_flow(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Suricata flow event.
    
    Flow events contain network flow statistics and duration information.
    """
    timestamp_str = event.get("timestamp", "")
    flow_data = event.get("flow", {})
    
    parsed = {
        "timestamp": _parse_timestamp(timestamp_str),
        "event_type": "flow",
        "flow_id": event.get("flow_id"),
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dst_ip": event.get("dest_ip"),
        "dst_port": event.get("dest_port"),
        "protocol": event.get("proto"),
        "bytes_in": flow_data.get("bytes_toclient", 0),
        "bytes_out": flow_data.get("bytes_toserver", 0),
        "packet_count": (flow_data.get("pkts_toclient", 0) + 
                        flow_data.get("pkts_toserver", 0)),
        "duration_seconds": flow_data.get("duration", 0),
        "flow_state": flow_data.get("state", "unknown"),
        "reason": flow_data.get("reason", ""),
        "tags": event.get("tags", []),
        "raw_data": event
    }
    
    return parsed


def _parse_dns(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Suricata DNS event.
    
    DNS events contain query/response information for network troubleshooting.
    """
    timestamp_str = event.get("timestamp", "")
    dns_data = event.get("dns", {})
    
    parsed = {
        "timestamp": _parse_timestamp(timestamp_str),
        "event_type": "dns",
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dst_ip": event.get("dest_ip"),
        "dst_port": event.get("dest_port"),
        "protocol": "dns",
        "query": dns_data.get("query", {}).get("name", ""),
        "query_type": dns_data.get("query", {}).get("type", ""),
        "response_code": dns_data.get("response", {}).get("code", ""),
        "answers": dns_data.get("response", {}).get("answers", []),
        "tags": event.get("tags", []),
        "raw_data": event
    }
    
    return parsed


def _parse_http(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Suricata HTTP event.
    
    HTTP events contain application-layer protocol details.
    """
    timestamp_str = event.get("timestamp", "")
    http_data = event.get("http", {})
    
    parsed = {
        "timestamp": _parse_timestamp(timestamp_str),
        "event_type": "http",
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dst_ip": event.get("dest_ip"),
        "dst_port": event.get("dest_port"),
        "protocol": "http",
        "http_method": http_data.get("http_method", ""),
        "http_uri": http_data.get("uri", ""),
        "http_host": http_data.get("hostname", ""),
        "http_status": http_data.get("status", 0),
        "user_agent": http_data.get("http_user_agent", ""),
        "tags": event.get("tags", []),
        "raw_data": event
    }
    
    return parsed


def _parse_tls(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Suricata TLS event.
    
    TLS events contain SSL/TLS handshake and certificate information.
    """
    timestamp_str = event.get("timestamp", "")
    tls_data = event.get("tls", {})
    
    parsed = {
        "timestamp": _parse_timestamp(timestamp_str),
        "event_type": "tls",
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dst_ip": event.get("dest_ip"),
        "dst_port": event.get("dest_port"),
        "protocol": "tls",
        "tls_version": tls_data.get("version", ""),
        "tls_sni": tls_data.get("sni", ""),
        "tls_subject": tls_data.get("subject", ""),
        "tls_issuer": tls_data.get("issuer", ""),
        "tls_fingerprint": tls_data.get("fingerprint", ""),
        "tags": event.get("tags", []),
        "raw_data": event
    }
    
    return parsed


def _parse_generic(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse generic Suricata event (fallback for unknown types).
    """
    timestamp_str = event.get("timestamp", "")
    
    return {
        "timestamp": _parse_timestamp(timestamp_str),
        "event_type": event.get("event_type", "generic"),
        "src_ip": event.get("src_ip"),
        "src_port": event.get("src_port"),
        "dst_ip": event.get("dest_ip"),
        "dst_port": event.get("dest_port"),
        "protocol": event.get("proto"),
        "tags": event.get("tags", []),
        "raw_data": event
    }


def _parse_timestamp(timestamp_str: str) -> str:
    """
    Parse Suricata timestamp string (ISO 8601 format).
    
    Args:
        timestamp_str: ISO 8601 timestamp string
        
    Returns:
        ISO 8601 formatted timestamp string
    """
    try:
        if timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.isoformat()
    except (ValueError, AttributeError):
        pass
    
    return datetime.utcnow().isoformat() + "Z"
