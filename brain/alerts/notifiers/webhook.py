"""
Webhook Alert Notifier
======================
Sends alert notifications via HTTP webhooks.
Extensible for Slack, email, PagerDuty, and custom endpoints.

Author: HungryHoundDog Team
"""

import logging
from typing import List, Dict, Optional
import requests
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WebhookNotifier:
    """Send alerts via HTTP webhooks."""
    
    def __init__(self, webhook_urls: List[str], timeout: int = 10):
        """
        Initialize webhook notifier.
        
        Args:
            webhook_urls: List of webhook URLs
            timeout: Request timeout in seconds
        """
        self.webhook_urls = webhook_urls
        self.timeout = timeout
        
        logger.info(f"Initialized WebhookNotifier with {len(webhook_urls)} endpoints")
    
    def notify(self, alerts: List[Dict]) -> bool:
        """
        Send alerts to all registered webhooks.
        
        Args:
            alerts: List of alerts to send
            
        Returns:
            True if at least one webhook succeeded
        """
        if not alerts:
            return True
        
        success_count = 0
        
        for webhook_url in self.webhook_urls:
            try:
                self._send_to_webhook(webhook_url, alerts)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send to webhook {webhook_url}: {str(e)}")
        
        return success_count > 0
    
    def _send_to_webhook(self, webhook_url: str, alerts: List[Dict]) -> None:
        """
        Send alerts to a single webhook.
        
        Args:
            webhook_url: Webhook URL
            alerts: List of alerts
        """
        # Format payload based on webhook type
        if "slack" in webhook_url.lower():
            payload = self._format_slack(alerts)
        elif "pagerduty" in webhook_url.lower():
            payload = self._format_pagerduty(alerts)
        else:
            payload = self._format_generic(alerts)
        
        # Send request
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        logger.info(f"Sent {len(alerts)} alerts to {webhook_url}")
    
    def _format_generic(self, alerts: List[Dict]) -> Dict:
        """
        Format alerts for generic HTTP webhook.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Formatted payload
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_count": len(alerts),
            "alerts": [
                {
                    "type": alert.get("alert_type"),
                    "severity": alert.get("severity"),
                    "message": alert.get("alert_message"),
                    "src_ip": alert.get("src_ip"),
                    "dst_ip": alert.get("dst_ip"),
                    "timestamp": alert.get("timestamp")
                }
                for alert in alerts
            ]
        }
    
    def _format_slack(self, alerts: List[Dict]) -> Dict:
        """
        Format alerts for Slack webhook.
        
        Args:
            alerts: List of alerts
            
        Returns:
            Slack message payload
        """
        # Color based on severity
        severity_colors = {
            "critical": "#ff0000",
            "high": "#ff6600",
            "medium": "#ffaa00",
            "low": "#00aa00"
        }
        
        # Group by severity
        by_severity = {}
        for alert in alerts:
            severity = alert.get("severity", "unknown")
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(alert)
        
        # Build message
        attachments = []
        
        for severity, severity_alerts in by_severity.items():
            color = severity_colors.get(severity, "#999999")
            
            # Build alert text
            alert_text = ""
            for alert in severity_alerts[:5]:  # Limit to 5 per severity
                alert_text += (
                    f"• {alert.get('alert_message', 'Unknown')}\n"
                    f"  From: {alert.get('src_ip')}:{alert.get('src_port', 'N/A')} "
                    f"To: {alert.get('dst_ip')}:{alert.get('dst_port', 'N/A')}\n"
                )
            
            if len(severity_alerts) > 5:
                alert_text += f"• ... and {len(severity_alerts) - 5} more\n"
            
            attachments.append({
                "color": color,
                "title": f"{severity.upper()} Severity ({len(severity_alerts)} alerts)",
                "text": alert_text,
                "ts": int(datetime.now(timezone.utc).timestamp())
            })
        
        return {
            "text": f"HungryHoundDog Security Alerts: {len(alerts)} new alerts",
            "attachments": attachments
        }
    
    def _format_pagerduty(self, alerts: List[Dict]) -> Dict:
        """
        Format alerts for PagerDuty.
        
        Args:
            alerts: List of alerts
            
        Returns:
            PagerDuty event payload
        """
        # Take highest severity alert
        highest_severity = "low"
        highest_alert = alerts[0] if alerts else {}
        
        severity_priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        
        for alert in alerts:
            severity = alert.get("severity", "low")
            if severity_priority.get(severity, 99) < severity_priority.get(highest_severity, 99):
                highest_severity = severity
                highest_alert = alert
        
        # Map to PagerDuty severity
        pd_severity_map = {
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info"
        }
        
        return {
            "routing_key": "your_routing_key",  # Should be configured
            "event_action": "trigger",
            "dedup_key": f"{highest_alert.get('src_ip')}:{highest_alert.get('dst_ip')}",
            "payload": {
                "summary": f"{highest_severity.upper()}: {highest_alert.get('alert_message')}",
                "timestamp": highest_alert.get("timestamp"),
                "severity": pd_severity_map.get(highest_severity, "warning"),
                "source": "HungryHoundDog",
                "custom_details": {
                    "alert_count": len(alerts),
                    "source_ip": highest_alert.get("src_ip"),
                    "destination_ip": highest_alert.get("dst_ip"),
                    "alert_type": highest_alert.get("alert_type")
                }
            }
        }
    
    def add_webhook(self, webhook_url: str) -> None:
        """
        Add a new webhook endpoint.
        
        Args:
            webhook_url: Webhook URL to add
        """
        if webhook_url not in self.webhook_urls:
            self.webhook_urls.append(webhook_url)
            logger.info(f"Added webhook: {webhook_url}")
    
    def remove_webhook(self, webhook_url: str) -> None:
        """
        Remove a webhook endpoint.
        
        Args:
            webhook_url: Webhook URL to remove
        """
        if webhook_url in self.webhook_urls:
            self.webhook_urls.remove(webhook_url)
            logger.info(f"Removed webhook: {webhook_url}")


class SlackNotifier(WebhookNotifier):
    """Slack-specific alert notifier."""
    
    def __init__(self, slack_webhook_url: str):
        """
        Initialize Slack notifier.
        
        Args:
            slack_webhook_url: Slack incoming webhook URL
        """
        super().__init__([slack_webhook_url])
    
    def notify(self, alerts: List[Dict]) -> bool:
        """Send alerts to Slack."""
        if not alerts:
            return True
        
        try:
            payload = self._format_slack(alerts)
            response = requests.post(
                self.webhook_urls[0],
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"Sent {len(alerts)} alerts to Slack")
            return True
        except Exception as e:
            logger.error(f"Slack notification failed: {str(e)}")
            return False


class EmailNotifier:
    """Email alert notifier (stub for extensibility)."""
    
    def __init__(self, smtp_config: Dict):
        """
        Initialize email notifier.
        
        Args:
            smtp_config: SMTP configuration
        """
        self.smtp_config = smtp_config
        logger.info("Email notifier initialized")
    
    def notify(self, alerts: List[Dict]) -> bool:
        """Send alerts via email."""
        logger.info(f"Email notification for {len(alerts)} alerts (not implemented)")
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    notifier = WebhookNotifier([
        "http://localhost:8000/webhook"
    ])
    
    sample_alerts = [
        {
            "alert_type": "rule_based",
            "severity": "high",
            "alert_message": "SQL Injection attempt detected",
            "src_ip": "192.168.1.100",
            "dst_ip": "10.0.0.50",
            "src_port": 54321,
            "dst_port": 443,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    notifier.notify(sample_alerts)
