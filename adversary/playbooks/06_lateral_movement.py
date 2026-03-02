#!/usr/bin/env python3
"""
06_lateral_movement.py: Simulated lateral movement across network segments.

Scans for additional hosts, attempts SSH pivots, and tries to move between
network segments to simulate post-compromise lateral movement.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import nmap
import paramiko
from paramiko import SSHException, AuthenticationException

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LateralMovement:
    """Simulates lateral movement and network pivoting."""

    def __init__(self, initial_host: str = "192.168.1.50"):
        """
        Initialize lateral movement module.

        Args:
            initial_host: Initially compromised host.
        """
        self.initial_host = initial_host
        self.nm = nmap.PortScanner()
        self.movement_log = []
        self.compromised_hosts = [initial_host]

    def scan_for_targets(self, network: str = "192.168.1.0/24") -> List[str]:
        """
        Scan network for additional targets.

        Args:
            network: CIDR network to scan.

        Returns:
            List of discovered hosts.
        """
        try:
            logger.warning(f"Scanning for lateral movement targets: {network}")

            self.nm.scan(
                hosts=network,
                arguments="-sV -p 22,3389,5985 --min-hostgroup 64"
            )

            discovered_hosts = []
            for host in self.nm.all_hosts():
                if self.nm[host].state() == 'up' and host != self.initial_host:
                    discovered_hosts.append(host)
                    logger.warning(f"Discovered target: {host}")

            return discovered_hosts

        except Exception as e:
            logger.error(f"Scan failed: {str(e)}")
            return []

    def attempt_ssh_pivot(
        self,
        target_host: str,
        username: str = "admin",
        password: str = "password"
    ) -> bool:
        """
        Attempt SSH pivot to new host.

        Args:
            target_host: Target host IP.
            username: SSH username.
            password: SSH password.

        Returns:
            True if pivot successful, False otherwise.
        """
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        movement_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "movement_type": "ssh_pivot",
            "from_host": self.initial_host,
            "target_host": target_host,
            "username": username,
            "success": False
        }

        try:
            ssh_client.connect(
                hostname=target_host,
                port=22,
                username=username,
                password=password,
                timeout=5,
                allow_agent=False,
                look_for_keys=False
            )

            logger.warning(f"PIVOT SUCCESS: {target_host} compromised")
            movement_record["success"] = True
            self.movement_log.append(movement_record)
            self.compromised_hosts.append(target_host)
            ssh_client.close()
            return True

        except (AuthenticationException, SSHException, Exception) as e:
            logger.debug(f"Pivot failed to {target_host}: {str(e)}")
            movement_record["error"] = str(e)
            self.movement_log.append(movement_record)
            return False

    def discover_network_info(self, host: str) -> Optional[Dict[str, Any]]:
        """
        Discover network information from compromised host.

        Args:
            host: Compromised host IP.

        Returns:
            Dictionary with network discovery info.
        """
        logger.warning(f"Discovering network info from {host}")

        discovery_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "discovery_type": "network_enumeration",
            "source_host": host,
            "findings": {
                "internal_networks": ["192.168.1.0/24", "192.168.10.0/24"],
                "gateway": "192.168.1.1",
                "dns_servers": ["8.8.8.8", "8.8.4.4"],
                "connected_systems": ["PLC_1", "HMI_2", "RTU_3"]
            }
        }

        self.movement_log.append(discovery_record)
        return discovery_record

    def execute_lateral_movement_campaign(self) -> Dict[str, Any]:
        """
        Execute complete lateral movement campaign.

        Returns:
            Summary of movement campaign.
        """
        logger.warning("=== INITIATING LATERAL MOVEMENT CAMPAIGN ===")

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "initial_compromise": self.initial_host,
            "campaign_stages": []
        }

        # Stage 1: Network scan
        logger.warning("Stage 1: Scanning for additional targets...")
        targets = self.scan_for_targets(network="192.168.1.0/24")
        summary["targets_discovered"] = len(targets)
        time.sleep(2)

        # Stage 2: Pivot attempts
        logger.warning(f"Stage 2: Attempting SSH pivots to {len(targets)} targets...")
        pivot_attempts = 0
        successful_pivots = 0

        for target in targets[:5]:  # Limit to 5 pivots
            if self.attempt_ssh_pivot(target_host=target):
                successful_pivots += 1
            pivot_attempts += 1
            time.sleep(1)

        summary["pivot_attempts"] = pivot_attempts
        summary["successful_pivots"] = successful_pivots

        # Stage 3: Network reconnaissance from each compromised host
        logger.warning("Stage 3: Network discovery from compromised hosts...")
        for host in self.compromised_hosts:
            self.discover_network_info(host)
            time.sleep(1)

        summary["compromised_hosts"] = self.compromised_hosts
        summary["total_hosts_compromised"] = len(self.compromised_hosts)
        summary["movement_events_logged"] = len(self.movement_log)

        logger.warning(f"Campaign complete: {len(self.compromised_hosts)} hosts compromised")
        return summary

    def export_log(self, filepath: str) -> None:
        """Export movement log to JSON."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.movement_log, f, indent=2)
            logger.info(f"Movement log exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")


def main() -> int:
    """Execute lateral movement simulation."""
    try:
        campaign = LateralMovement(initial_host="192.168.1.50")
        summary = campaign.execute_lateral_movement_campaign()
        campaign.export_log("/tmp/lateral_movement.json")

        print(json.dumps(summary, indent=2))
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
