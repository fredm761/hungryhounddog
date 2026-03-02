#!/usr/bin/env python3
"""
01_recon_scan.py: Network discovery and port scanning playbook.

Performs nmap-based reconnaissance on the lab subnet and outputs
results in JSON format for downstream processing.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any

import nmap

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NetworkReconaissance:
    """Performs network discovery and port scanning."""

    def __init__(self, target_subnet: str = "192.168.1.0/24"):
        """
        Initialize reconnaissance scanner.

        Args:
            target_subnet: CIDR notation of target network.
        """
        self.target_subnet = target_subnet
        self.nm = nmap.PortScanner()
        self.results = {
            "scan_timestamp": datetime.utcnow().isoformat(),
            "target_subnet": target_subnet,
            "hosts": []
        }

    def scan_network(self) -> Dict[str, Any]:
        """
        Scan entire lab subnet for active hosts and open ports.

        Returns:
            Dictionary containing scan results.
        """
        try:
            logger.info(f"Starting network scan on {self.target_subnet}")
            self.nm.scan(
                hosts=self.target_subnet,
                arguments="-sV -p 22,80,443,502,1883,8080 --min-hostgroup 64 --max-hostgroup 256"
            )

            for host in self.nm.all_hosts():
                if self.nm[host].state() == 'up':
                    host_info = self._extract_host_info(host)
                    self.results["hosts"].append(host_info)
                    logger.info(f"Host {host} is up with {len(host_info['ports'])} open ports")

            logger.info(f"Scan complete: {len(self.results['hosts'])} hosts discovered")
            return self.results

        except Exception as e:
            logger.error(f"Scan failed: {str(e)}")
            raise

    def _extract_host_info(self, host: str) -> Dict[str, Any]:
        """
        Extract detailed information for a single host.

        Args:
            host: Target host IP address.

        Returns:
            Dictionary with host details and open ports.
        """
        host_data = {
            "ip": host,
            "hostname": self.nm[host].hostname(),
            "status": self.nm[host].state(),
            "ports": []
        }

        for proto in self.nm[host].all_protocols():
            ports = self.nm[host][proto].keys()
            for port in ports:
                port_state = self.nm[host][proto][port]['state']
                if port_state == 'open':
                    port_info = {
                        "port": port,
                        "protocol": proto,
                        "state": port_state,
                        "service": self.nm[host][proto][port].get('name', 'unknown'),
                        "version": self.nm[host][proto][port].get('version', '')
                    }
                    host_data["ports"].append(port_info)

        return host_data

    def export_json(self, filepath: str) -> None:
        """
        Export scan results to JSON file.

        Args:
            filepath: Output JSON file path.
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Results exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            raise


def main() -> int:
    """Execute network reconnaissance scan."""
    try:
        scanner = NetworkReconaissance(target_subnet="192.168.1.0/24")
        results = scanner.scan_network()
        scanner.export_json("/tmp/recon_results.json")

        print(json.dumps(results, indent=2))
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
