"""
Alert Manager
=============
Processes ML anomalies and Suricata rule alerts.
Handles deduplication, severity assignment, and notifier dispatch.

Author: HungryHoundDog Team
"""

import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import hashlib

from alerts.notifiers.webhook import WebhookNotifier
from detection.rules.correlation import AlertCorrelator

logger = logging.getLogger(__name__)


class AlertManager:
    """Manage and process security alerts."""
    
    # Alert severity levels
    SEVERITY_LEVELS = {
        "critical": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "info": 1
    }
    
    def __init__(self, dedup_window_seconds: int = 300):
        """
        Initialize alert manager.
        
        Args:
            dedup_window_seconds: Time window for deduplication
        """
        self.dedup_window = timedelta(seconds=dedup_window_seconds)
        self.alert_cache: Dict[str, datetime] = {}
        self.correlator = AlertCorrelator(time_window_seconds=dedup_window_seconds)
        self.notifiers = []
        self.processed_alerts = []
        
        logger.info("Alert manager initialized")
    
    def register_notifier(self, notifier) -> None:
        """
        Register an alert notifier.
        
        Args:
            notifier: Notifier instance
        """
        self.notifiers.append(notifier)
        logger.info(f"Registered notifier: {notifier.__class__.__name__}")
    
    def process_ml_alert(self, flow: Dict) -> Optional[Dict]:
        """
        Process ML-based anomaly alert.
        
        Args:
            flow: Network flow with anomaly score
            
        Returns:
            Processed alert or None if deduplicated
        """
        try:
            anomaly_score = flow.get("anomaly_score", 0.0)
            
            if anomaly_score < 0.5:
                return None  # Not anomalous
            
            # Determine severity based on score
            if anomaly_score > 0.9:
                severity = "critical"
            elif anomaly_score > 0.8:
                severity = "high"
            elif anomaly_score > 0.7:
                severity = "medium"
            else:
                severity = "low"
            
            # Create alert
            alert = {
                "alert_type": "ml_anomaly",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "src_ip": flow.get("src_ip"),
                "dst_ip": flow.get("dst_ip"),
                "src_port": flow.get("src_port"),
                "dst_port": flow.get("dst_port"),
                "protocol": flow.get("protocol"),
                "severity": severity,
                "severity_level": self.SEVERITY_LEVELS.get(severity, 0),
                "alert_message": f"Anomalous network flow detected (score: {anomaly_score:.2%})",
                "anomaly_score": anomaly_score,
                "raw_flow": flow
            }
            
            # Deduplicate
            if not self._should_deduplicate(alert):
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"ML alert processing error: {str(e)}")
            return None
    
    def process_rule_alert(self, suricata_alert: Dict) -> Optional[Dict]:
        """
        Process Suricata rule-based alert.
        
        Args:
            suricata_alert: Alert from Suricata
            
        Returns:
            Processed alert or None if deduplicated
        """
        try:
            # Map Suricata severity to our levels
            suricata_severity = suricata_alert.get("severity", 3)
            severity_map = {1: "critical", 2: "high", 3: "medium", 4: "low"}
            severity = severity_map.get(suricata_severity, "low")
            
            # Create alert
            alert = {
                "alert_type": "rule_based",
                "timestamp": suricata_alert.get("timestamp"),
                "src_ip": suricata_alert.get("src_ip"),
                "dst_ip": suricata_alert.get("dst_ip"),
                "src_port": suricata_alert.get("src_port"),
                "dst_port": suricata_alert.get("dst_port"),
                "protocol": suricata_alert.get("protocol"),
                "severity": severity,
                "severity_level": self.SEVERITY_LEVELS.get(severity, 0),
                "alert_message": suricata_alert.get("alert_message"),
                "signature_id": suricata_alert.get("signature_id"),
                "category": suricata_alert.get("category"),
                "raw_alert": suricata_alert
            }
            
            # Deduplicate
            if not self._should_deduplicate(alert):
                return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Rule alert processing error: {str(e)}")
            return None
    
    def process_batch(self, alerts: List[Dict]) -> List[Dict]:
        """
        Process a batch of alerts.
        
        Args:
            alerts: List of alerts
            
        Returns:
            List of processed/not-deduplicated alerts
        """
        processed = []
        
        for alert in alerts:
            # Process based on type
            if alert.get("anomaly_score") is not None:
                result = self.process_ml_alert(alert)
            else:
                result = self.process_rule_alert(alert)
            
            if result:
                processed.append(result)
        
        # Correlate alerts
        if processed:
            correlated = self.correlator.correlate_alerts(processed)
            self.processed_alerts.extend(processed)
            
            # Dispatch to notifiers
            self._dispatch_alerts(processed)
        
        logger.info(f"Processed {len(processed)} non-deduplicated alerts from batch of {len(alerts)}")
        
        return processed
    
    def _should_deduplicate(self, alert: Dict) -> bool:
        """
        Check if alert should be deduplicated.
        
        Args:
            alert: Alert to check
            
        Returns:
            True if alert is a duplicate
        """
        alert_key = self._generate_alert_key(alert)
        now = datetime.now(timezone.utc)
        
        # Check if we've seen this alert recently
        if alert_key in self.alert_cache:
            last_seen = self.alert_cache[alert_key]
            time_diff = now - last_seen
            
            if time_diff < self.dedup_window:
                logger.debug(f"Deduplicating alert: {alert_key}")
                return True
        
        # Update cache
        self.alert_cache[alert_key] = now
        
        # Clean old entries
        self._cleanup_cache()
        
        return False
    
    def _generate_alert_key(self, alert: Dict) -> str:
        """
        Generate deduplication key for alert.
        
        Args:
            alert: Alert dictionary
            
        Returns:
            Deduplication key
        """
        key_parts = [
            alert.get("alert_type", ""),
            alert.get("src_ip", ""),
            alert.get("dst_ip", ""),
            alert.get("alert_message", "")
        ]
        
        key = ":".join(str(p) for p in key_parts)
        return hashlib.md5(key.encode()).hexdigest()
    
    def _cleanup_cache(self) -> None:
        """Remove stale entries from dedup cache."""
        now = datetime.now(timezone.utc)
        stale_keys = []
        
        for key, timestamp in self.alert_cache.items():
            if (now - timestamp) > self.dedup_window:
                stale_keys.append(key)
        
        for key in stale_keys:
            del self.alert_cache[key]
        
        if stale_keys:
            logger.debug(f"Cleaned {len(stale_keys)} stale cache entries")
    
    def _dispatch_alerts(self, alerts: List[Dict]) -> None:
        """
        Dispatch alerts to registered notifiers.
        
        Args:
            alerts: List of alerts to dispatch
        """
        for notifier in self.notifiers:
            try:
                notifier.notify(alerts)
            except Exception as e:
                logger.error(f"Notifier error ({notifier.__class__.__name__}): {str(e)}")
    
    def get_recent_alerts(self, hours: int = 1, severity: Optional[str] = None) -> List[Dict]:
        """
        Get recent alerts.
        
        Args:
            hours: Number of hours to look back
            severity: Filter by severity level
            
        Returns:
            List of recent alerts
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = []
        
        for alert in self.processed_alerts:
            try:
                alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
                
                if alert_time < cutoff_time:
                    continue
                
                if severity and alert.get("severity") != severity:
                    continue
                
                recent.append(alert)
            except (ValueError, AttributeError):
                continue
        
        return recent
    
    def get_alert_statistics(self) -> Dict:
        """
        Get alert statistics.
        
        Returns:
            Dictionary with alert statistics
        """
        stats = {
            "total_alerts": len(self.processed_alerts),
            "by_severity": defaultdict(int),
            "by_type": defaultdict(int),
            "by_ip": defaultdict(int)
        }
        
        for alert in self.processed_alerts:
            severity = alert.get("severity", "unknown")
            alert_type = alert.get("alert_type", "unknown")
            src_ip = alert.get("src_ip", "unknown")
            
            stats["by_severity"][severity] += 1
            stats["by_type"][alert_type] += 1
            stats["by_ip"][src_ip] += 1
        
        return stats


def create_alert_manager(webhook_urls: List[str] = None) -> AlertManager:
    """
    Create and configure alert manager.
    
    Args:
        webhook_urls: List of webhook URLs for notifications
        
    Returns:
        Configured AlertManager
    """
    manager = AlertManager()
    
    # Register webhook notifier if URLs provided
    if webhook_urls:
        webhook_notifier = WebhookNotifier(webhook_urls)
        manager.register_notifier(webhook_notifier)
    
    return manager


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    manager = create_alert_manager()
    
    sample_ml_alert = {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.50",
        "src_port": 54321,
        "dst_port": 80,
        "protocol": "tcp",
        "anomaly_score": 0.95,
        "bytes_in": 5000,
        "bytes_out": 1000
    }
    
    processed = manager.process_ml_alert(sample_ml_alert)
    if processed:
        print(f"Processed alert: {processed['alert_message']}")
