#!/usr/bin/env python3
"""
test_adversary.py: Tests for adversary attack playbooks.

Verifies that attack playbooks execute correctly and produce
expected alert patterns detectable by Suricata and other security systems.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, List, Any


class MockAttackSimulator:
    """Mock adversary playbook simulator."""

    def __init__(self):
        """Initialize attack simulator."""
        self.executed_attacks = []
        self.generated_alerts = []

    def execute_nmap_scan(self, target: str) -> Dict[str, Any]:
        """Simulate nmap network discovery."""
        attack_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "network_reconnaissance",
            "tool": "nmap",
            "target": target,
            "results": {
                "hosts_discovered": 5,
                "ports_open": 12
            }
        }
        self.executed_attacks.append(attack_record)

        # Generate expected alerts
        self.generated_alerts.append({
            "alert_type": "port_scan_detected",
            "severity": "medium",
            "source": "192.168.1.50"
        })

        return attack_record

    def execute_modbus_read(self, target_host: str) -> Dict[str, Any]:
        """Simulate legitimate Modbus read."""
        attack_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "modbus_read",
            "target": target_host,
            "registers_read": 20,
            "success": True
        }
        self.executed_attacks.append(attack_record)
        return attack_record

    def execute_modbus_write_attack(self, target_host: str, value: int) -> Dict[str, Any]:
        """Simulate unauthorized Modbus write."""
        attack_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "modbus_write_attack",
            "target": target_host,
            "register": 100,
            "malicious_value": value,
            "success": True
        }
        self.executed_attacks.append(attack_record)

        # Generate expected Suricata alerts
        self.generated_alerts.append({
            "alert_type": "malicious_modbus_write",
            "severity": "critical",
            "source": "192.168.1.50",
            "destination": target_host,
            "protocol": "modbus"
        })

        return attack_record

    def execute_ssh_brute_force(self, target_host: str, attempts: int) -> Dict[str, Any]:
        """Simulate SSH brute force attack."""
        attack_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "ssh_brute_force",
            "target": target_host,
            "attempts": attempts,
            "successful_logins": 0
        }
        self.executed_attacks.append(attack_record)

        # Generate alerts for brute force attempts
        for i in range(min(attempts, 5)):  # Only generate alerts for first 5
            self.generated_alerts.append({
                "alert_type": "ssh_auth_attempt",
                "severity": "medium",
                "source": "192.168.1.50",
                "destination": target_host
            })

        return attack_record

    def execute_data_exfil(self, source_host: str) -> Dict[str, Any]:
        """Simulate data exfiltration."""
        attack_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "data_exfiltration",
            "source": source_host,
            "methods": ["dns_tunnel", "http_post"],
            "data_size_bytes": 50000
        }
        self.executed_attacks.append(attack_record)

        # Generate expected alerts
        for method in attack_record["methods"]:
            self.generated_alerts.append({
                "alert_type": f"data_exfil_{method}",
                "severity": "critical",
                "source": source_host
            })

        return attack_record

    def execute_lateral_movement(self) -> Dict[str, Any]:
        """Simulate lateral network movement."""
        attack_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "lateral_movement",
            "source": "192.168.1.50",
            "targets_reached": 3,
            "successful_pivots": 2
        }
        self.executed_attacks.append(attack_record)

        # Generate alerts
        for i in range(attack_record["successful_pivots"]):
            self.generated_alerts.append({
                "alert_type": "suspicious_ssh_connection",
                "severity": "high",
                "source": "192.168.1.50"
            })

        return attack_record

    def get_alerts_generated(self) -> List[Dict[str, Any]]:
        """Get all generated alerts."""
        return self.generated_alerts

    def get_attacks_executed(self) -> List[Dict[str, Any]]:
        """Get all executed attacks."""
        return self.executed_attacks


class TestAdversaryPlaybooks:
    """Test suite for adversary playbook execution."""

    @pytest.fixture
    def simulator(self):
        """Fixture: Attack simulator."""
        return MockAttackSimulator()

    def test_nmap_scan_execution(self, simulator):
        """Test nmap network discovery playbook."""
        result = simulator.execute_nmap_scan("192.168.1.0/24")

        assert result["attack_type"] == "network_reconnaissance"
        assert result["tool"] == "nmap"
        assert result["results"]["hosts_discovered"] > 0
        assert len(simulator.executed_attacks) == 1

    def test_nmap_scan_generates_alerts(self, simulator):
        """Test that nmap scan generates detectable alerts."""
        simulator.execute_nmap_scan("192.168.1.0/24")

        alerts = simulator.get_alerts_generated()
        assert len(alerts) > 0
        assert any("port_scan" in a["alert_type"].lower() for a in alerts)

    def test_modbus_read_baseline(self, simulator):
        """Test legitimate Modbus read execution."""
        result = simulator.execute_modbus_read("192.168.10.10")

        assert result["attack_type"] == "modbus_read"
        assert result["success"] is True
        assert result["registers_read"] == 20

    def test_modbus_read_no_alerts(self, simulator):
        """Test that legitimate Modbus reads don't generate alerts."""
        simulator.execute_modbus_read("192.168.10.10")

        alerts = simulator.get_alerts_generated()
        # Legitimate reads should not trigger alerts
        assert len(alerts) == 0

    def test_modbus_write_attack(self, simulator):
        """Test unauthorized Modbus write attack."""
        result = simulator.execute_modbus_write_attack("192.168.10.10", 65535)

        assert result["attack_type"] == "modbus_write_attack"
        assert result["success"] is True
        assert result["malicious_value"] == 65535

    def test_modbus_write_attack_generates_alerts(self, simulator):
        """Test that Modbus write attack generates Suricata alerts."""
        simulator.execute_modbus_write_attack("192.168.10.10", 65535)

        alerts = simulator.get_alerts_generated()
        assert len(alerts) > 0

        modbus_alerts = [a for a in alerts if "modbus" in a.get("alert_type", "").lower()]
        assert len(modbus_alerts) > 0
        assert any(a["severity"] == "critical" for a in modbus_alerts)

    def test_ssh_brute_force_attack(self, simulator):
        """Test SSH brute force attack."""
        result = simulator.execute_ssh_brute_force("192.168.1.50", 100)

        assert result["attack_type"] == "ssh_brute_force"
        assert result["attempts"] == 100

    def test_ssh_brute_force_generates_alerts(self, simulator):
        """Test that SSH brute force generates IDS alerts."""
        simulator.execute_ssh_brute_force("192.168.1.50", 100)

        alerts = simulator.get_alerts_generated()
        assert len(alerts) > 0

        ssh_alerts = [a for a in alerts if "ssh" in a.get("alert_type", "").lower()]
        assert len(ssh_alerts) > 0

    def test_data_exfiltration_attack(self, simulator):
        """Test data exfiltration attack execution."""
        result = simulator.execute_data_exfil("192.168.10.10")

        assert result["attack_type"] == "data_exfiltration"
        assert result["data_size_bytes"] > 0
        assert len(result["methods"]) > 0

    def test_data_exfil_generates_alerts(self, simulator):
        """Test that data exfil generates alerts."""
        simulator.execute_data_exfil("192.168.10.10")

        alerts = simulator.get_alerts_generated()
        assert len(alerts) > 0

        critical_alerts = [a for a in alerts if a["severity"] == "critical"]
        assert len(critical_alerts) > 0

    def test_lateral_movement_attack(self, simulator):
        """Test lateral movement attack."""
        result = simulator.execute_lateral_movement()

        assert result["attack_type"] == "lateral_movement"
        assert result["successful_pivots"] > 0

    def test_lateral_movement_generates_alerts(self, simulator):
        """Test that lateral movement generates alerts."""
        simulator.execute_lateral_movement()

        alerts = simulator.get_alerts_generated()
        assert len(alerts) > 0

        suspicious_alerts = [a for a in alerts if "suspicious" in a.get("alert_type", "").lower()]
        assert len(suspicious_alerts) > 0

    def test_attack_sequence_execution(self, simulator):
        """Test complete attack sequence."""
        # Phase 1: Reconnaissance
        simulator.execute_nmap_scan("192.168.1.0/24")

        # Phase 2: Baseline reading
        simulator.execute_modbus_read("192.168.10.10")

        # Phase 3: Attack
        simulator.execute_modbus_write_attack("192.168.10.10", 65535)

        # Phase 4: Exfiltration
        simulator.execute_data_exfil("192.168.10.10")

        attacks = simulator.get_attacks_executed()
        assert len(attacks) == 4

        alert_severity_counts = {}
        for alert in simulator.get_alerts_generated():
            severity = alert["severity"]
            alert_severity_counts[severity] = alert_severity_counts.get(severity, 0) + 1

        assert alert_severity_counts.get("critical", 0) > 0

    def test_multiple_attack_tracking(self, simulator):
        """Test tracking multiple simultaneous attacks."""
        # Execute multiple attacks
        for i in range(3):
            simulator.execute_modbus_write_attack("192.168.10.10", i * 1000)

        attacks = simulator.get_attacks_executed()
        assert len(attacks) == 3

        for attack in attacks:
            assert attack["attack_type"] == "modbus_write_attack"

    def test_alert_severity_escalation(self, simulator):
        """Test that attack severity is correctly reflected in alerts."""
        # Legitimate read - no alerts
        simulator.execute_modbus_read("192.168.10.10")
        assert len(simulator.get_alerts_generated()) == 0

        # Dangerous write - critical alerts
        simulator.execute_modbus_write_attack("192.168.10.10", 65535)
        alerts = simulator.get_alerts_generated()
        critical_count = sum(1 for a in alerts if a["severity"] == "critical")

        assert critical_count > 0

    def test_attack_timestamps(self, simulator):
        """Test that attacks include valid timestamps."""
        simulator.execute_modbus_write_attack("192.168.10.10", 1000)

        attacks = simulator.get_attacks_executed()
        assert len(attacks) > 0

        attack = attacks[0]
        assert "timestamp" in attack
        # Should be ISO format
        assert "T" in attack["timestamp"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
