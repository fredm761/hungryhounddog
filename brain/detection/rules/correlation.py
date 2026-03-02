"""
Rule-Based Alert Correlation
=============================
Groups related alerts by source IP, time window, and attack phase.
Maps alerts to MITRE ATT&CK tactics and techniques.

Author: HungryHoundDog Team
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


class AlertCorrelator:
    """Correlate related security alerts into cohesive patterns."""
    
    # MITRE ATT&CK mapping
    MITRE_MAPPING = {
        "reconnaissance": {
            "port_scan": "T1046",
            "network_discovery": "T1040",
            "enumeration": "T1087"
        },
        "initial_access": {
            "exploit": "T1190",
            "phishing": "T1566",
            "external_rdu": "T1133"
        },
        "execution": {
            "command_execution": "T1059",
            "exploitation": "T1190"
        },
        "persistence": {
            "account_creation": "T1098",
            "privilege_escalation": "T1548"
        },
        "privilege_escalation": {
            "elevation": "T1548",
            "exploitation": "T1190"
        },
        "defense_evasion": {
            "firewall_evasion": "T1562",
            "obfuscation": "T1027"
        },
        "credential_access": {
            "sniffing": "T1040",
            "brute_force": "T1110"
        },
        "discovery": {
            "network_discovery": "T1040",
            "system_discovery": "T1082"
        },
        "lateral_movement": {
            "lateral_movement": "T1570",
            "remote_access": "T1021"
        },
        "exfiltration": {
            "data_exfiltration": "T1020",
            "dns_exfiltration": "T1048"
        }
    }
    
    def __init__(self, time_window_seconds: int = 300):
        """
        Initialize alert correlator.
        
        Args:
            time_window_seconds: Time window for grouping related alerts
        """
        self.time_window = timedelta(seconds=time_window_seconds)
        self.alert_groups = []
    
    def correlate_alerts(self, alerts: List[Dict]) -> List[Dict]:
        """
        Correlate multiple alerts into attack patterns.
        
        Args:
            alerts: List of alert dictionaries
            
        Returns:
            List of correlated alert groups
        """
        if not alerts:
            return []
        
        # Group alerts by source IP and time window
        groups = self._group_by_source_and_time(alerts)
        
        # Analyze each group for attack phases
        correlated = []
        for group in groups:
            correlation = self._analyze_group(group)
            if correlation:
                correlated.append(correlation)
        
        logger.info(f"Correlated {len(alerts)} alerts into {len(correlated)} groups")
        return correlated
    
    def _group_by_source_and_time(self, alerts: List[Dict]) -> List[List[Dict]]:
        """
        Group alerts by source IP and time proximity.
        
        Args:
            alerts: List of alerts
            
        Returns:
            List of alert groups
        """
        # Sort by timestamp
        sorted_alerts = sorted(
            alerts,
            key=lambda a: self._parse_timestamp(a.get("timestamp"))
        )
        
        groups = defaultdict(list)
        
        for alert in sorted_alerts:
            src_ip = alert.get("src_ip", "unknown")
            groups[src_ip].append(alert)
        
        # Split each source IP group by time windows
        result = []
        for src_ip, ip_alerts in groups.items():
            time_groups = self._split_by_time_window(ip_alerts)
            result.extend(time_groups)
        
        return result
    
    def _split_by_time_window(self, alerts: List[Dict]) -> List[List[Dict]]:
        """
        Split alerts into time windows.
        
        Args:
            alerts: Sorted list of alerts
            
        Returns:
            List of time-windowed groups
        """
        if not alerts:
            return []
        
        groups = []
        current_group = [alerts[0]]
        last_time = self._parse_timestamp(alerts[0].get("timestamp"))
        
        for alert in alerts[1:]:
            current_time = self._parse_timestamp(alert.get("timestamp"))
            time_diff = current_time - last_time
            
            if time_diff <= self.time_window:
                current_group.append(alert)
            else:
                groups.append(current_group)
                current_group = [alert]
            
            last_time = current_time
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _analyze_group(self, alerts: List[Dict]) -> Dict:
        """
        Analyze a group of related alerts for attack patterns.
        
        Args:
            alerts: Group of related alerts
            
        Returns:
            Correlated alert dictionary or None
        """
        if not alerts:
            return None
        
        src_ip = alerts[0].get("src_ip", "unknown")
        dst_ips = set(a.get("dst_ip") for a in alerts)
        
        # Detect attack phase
        attack_phase = self._detect_phase(alerts)
        mitre_technique = self._get_mitre_technique(attack_phase)
        
        # Calculate severity
        severity = max(a.get("severity", 0) for a in alerts)
        
        # Build correlation
        correlation = {
            "correlation_id": self._generate_correlation_id(alerts),
            "attack_phase": attack_phase,
            "mitre_tactic": attack_phase,
            "mitre_technique": mitre_technique,
            "src_ip": src_ip,
            "target_ips": list(dst_ips),
            "target_count": len(dst_ips),
            "alert_count": len(alerts),
            "severity": severity,
            "timestamp_start": alerts[0].get("timestamp"),
            "timestamp_end": alerts[-1].get("timestamp"),
            "alert_signatures": [a.get("alert_message", "") for a in alerts],
            "confidence": self._calculate_confidence(alerts, attack_phase)
        }
        
        return correlation
    
    def _detect_phase(self, alerts: List[Dict]) -> str:
        """
        Detect the attack phase from alert patterns.
        
        Args:
            alerts: Group of alerts
            
        Returns:
            Attack phase name
        """
        alert_messages = [a.get("alert_message", "").lower() for a in alerts]
        
        # Heuristics for phase detection
        if any("scan" in msg or "nmap" in msg for msg in alert_messages):
            return "reconnaissance"
        elif any("exploit" in msg for msg in alert_messages):
            return "execution"
        elif any("malware" in msg or "backdoor" in msg for msg in alert_messages):
            return "persistence"
        elif any("lateral" in msg or "psexec" in msg for msg in alert_messages):
            return "lateral_movement"
        elif any("exfiltration" in msg or "dns_query" in msg for msg in alert_messages):
            return "exfiltration"
        else:
            return "unknown"
    
    def _get_mitre_technique(self, phase: str) -> str:
        """
        Get MITRE ATT&CK technique for attack phase.
        
        Args:
            phase: Attack phase
            
        Returns:
            MITRE technique ID
        """
        techniques = self.MITRE_MAPPING.get(phase, {})
        if techniques:
            # Return first technique ID
            return list(techniques.values())[0]
        return "Unknown"
    
    def _calculate_confidence(self, alerts: List[Dict], phase: str) -> float:
        """
        Calculate confidence score for correlation.
        
        Args:
            alerts: Group of alerts
            phase: Detected attack phase
            
        Returns:
            Confidence score (0-1)
        """
        # Multiple alerts increase confidence
        alert_factor = min(len(alerts) / 5.0, 1.0)
        
        # Known phases increase confidence
        phase_factor = 0.8 if phase != "unknown" else 0.5
        
        # Consistent IPs increase confidence
        src_ips = set(a.get("src_ip") for a in alerts)
        ip_factor = 1.0 if len(src_ips) == 1 else 0.7
        
        confidence = (alert_factor + phase_factor + ip_factor) / 3.0
        return min(confidence, 1.0)
    
    def _generate_correlation_id(self, alerts: List[Dict]) -> str:
        """
        Generate unique correlation ID.
        
        Args:
            alerts: Group of alerts
            
        Returns:
            Unique correlation ID
        """
        src_ip = alerts[0].get("src_ip", "")
        timestamp = alerts[0].get("timestamp", "")
        key = f"{src_ip}:{timestamp}:{len(alerts)}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime.
        
        Args:
            timestamp_str: Timestamp string
            
        Returns:
            Datetime object
        """
        try:
            if isinstance(timestamp_str, datetime):
                return timestamp_str
            
            # Try ISO format
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt
        except (ValueError, AttributeError, TypeError):
            return datetime.now(timezone.utc)


def correlate_alerts(alerts: List[Dict]) -> List[Dict]:
    """
    Convenience function to correlate alerts.
    
    Args:
        alerts: List of alert dictionaries
        
    Returns:
        List of correlated alert groups
    """
    correlator = AlertCorrelator(time_window_seconds=300)
    return correlator.correlate_alerts(alerts)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    sample_alerts = [
        {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.50",
            "alert_message": "ET POLICY Nmap Scripting Engine User-Agent",
            "severity": 3,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.51",
            "alert_message": "ET POLICY Nmap Scripting Engine User-Agent",
            "severity": 3,
            "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        }
    ]
    
    correlations = correlate_alerts(sample_alerts)
    print(f"Found {len(correlations)} correlated alert groups")
