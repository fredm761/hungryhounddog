#!/usr/bin/env python3
"""
=============================================================================
HungryHoundDog — Health Check Agent
=============================================================================
Purpose:
    Collects system health metrics from the Raspberry Pi sensor and reports
    them as a JSON payload. This data tells the Brain (and you) whether
    the sensor is healthy: Is Suricata running? Is RAM tight? Is the disk
    filling up? Is eth0 still in promiscuous mode?

How it works:
    1. Gather CPU, RAM, and disk usage from the operating system.
    2. Check whether the Suricata process is running and collect its PID
       and memory usage.
    3. Check network interface status (eth0 promiscuous mode, wlan0 IP).
    4. Check eve.json file size and last-modified time.
    5. Package everything into a JSON payload.
    6. POST the payload to Brain's health endpoint (or write to local
       fallback file if Brain is unreachable).
    7. Print the JSON to stdout for manual inspection and debugging.

    This agent is designed to be run periodically by a systemd timer
    (every 60 seconds), NOT as a long-running daemon. This keeps its
    memory footprint near zero between runs — important on a 2 GB Pi.

Runs on:  Raspberry Pi 4 ("The Sensor")
Location: /home/alfredo/hungryhounddog/sensor/agent/health_check.py
Timer:    hungryhounddog-health.timer (systemd, every 60s)

Author:   Alfredo
Project:  HungryHoundDog — Weekend 2
=============================================================================
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# =============================================================================
# 0x1 — Configuration and Logging (reuses the same config.yaml)
# =============================================================================

def load_config(config_path: str) -> dict:
    """
    Reads the YAML configuration file and returns it as a dictionary.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def setup_logging(config: dict) -> logging.Logger:
    """
    Configures logging for the health check agent.
    """
    shared = config["shared"]
    log_level = getattr(logging, shared["log_level"].upper(), logging.INFO)
    log_file = Path(shared["log_file"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("health_check")
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# =============================================================================
# 0x2 — System Metrics Collection
# =============================================================================
# We read directly from /proc instead of using the 'psutil' library.
# Why: psutil would need to be pip-installed on the Pi (an extra dependency).
# The /proc filesystem is always available on Linux and gives us everything
# we need. This approach is lighter and more educational — you learn how
# Linux exposes system info to userspace programs.

def get_cpu_usage() -> dict:
    """
    Reads CPU usage from /proc/stat by taking two snapshots 0.5 seconds
    apart and calculating the percentage of time spent in non-idle states.

    Returns
    -------
    dict
        {"percent": float} — CPU usage as a percentage (0–100).

    How /proc/stat works:
        The first line looks like:
            cpu  user nice system idle iowait irq softirq steal guest guest_nice
        Each value is in units of USER_HZ (typically 1/100th of a second).
        'idle' + 'iowait' = time the CPU was doing nothing.
        Everything else = time the CPU was working.
        By comparing two snapshots, we get the usage over that interval.
    """
    def read_cpu_times():
        with open("/proc/stat", "r") as f:
            line = f.readline()  # First line: aggregate across all cores
        parts = line.split()
        # parts[0] = "cpu", parts[1:] = user, nice, system, idle, iowait, ...
        times = [int(x) for x in parts[1:]]
        idle = times[3] + times[4]  # idle + iowait
        total = sum(times)
        return idle, total

    idle1, total1 = read_cpu_times()
    time.sleep(0.5)
    idle2, total2 = read_cpu_times()

    idle_delta = idle2 - idle1
    total_delta = total2 - total1

    if total_delta == 0:
        return {"percent": 0.0}

    usage = ((total_delta - idle_delta) / total_delta) * 100
    return {"percent": round(usage, 1)}


def get_memory_usage() -> dict:
    """
    Reads memory statistics from /proc/meminfo.

    Returns
    -------
    dict
        {
            "total_mb": float,
            "available_mb": float,
            "used_mb": float,
            "percent": float  — percentage of RAM in use
        }

    Why 'MemAvailable' instead of 'MemFree':
        MemFree is the raw unused memory. MemAvailable is the kernel's
        estimate of how much memory is actually available for new
        applications (it includes reclaimable buffers and cache).
        MemAvailable is what matters for "is the Pi running out of RAM?"
    """
    meminfo = {}
    with open("/proc/meminfo", "r") as f:
        for line in f:
            parts = line.split()
            key = parts[0].rstrip(":")
            value_kb = int(parts[1])
            meminfo[key] = value_kb

    total_mb = meminfo["MemTotal"] / 1024
    available_mb = meminfo.get("MemAvailable", meminfo["MemFree"]) / 1024
    used_mb = total_mb - available_mb
    percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0

    return {
        "total_mb": round(total_mb, 1),
        "available_mb": round(available_mb, 1),
        "used_mb": round(used_mb, 1),
        "percent": round(percent, 1),
    }


def get_disk_usage(paths: list[str]) -> dict:
    """
    Reports disk usage for each configured path using os.statvfs().

    Parameters
    ----------
    paths : list[str]
        List of filesystem paths to check (e.g., "/", "/var/log/suricata").

    Returns
    -------
    dict
        Keyed by path. Each value is:
        {
            "total_gb": float,
            "used_gb": float,
            "free_gb": float,
            "percent": float
        }

    How os.statvfs works:
        Returns filesystem statistics for the partition containing the
        given path. f_blocks = total blocks, f_bfree = free blocks,
        f_frsize = block size in bytes. Multiply to get bytes.
    """
    result = {}
    for path in paths:
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            used = total - free
            percent = (used / total) * 100 if total > 0 else 0

            result[path] = {
                "total_gb": round(total / (1024 ** 3), 2),
                "used_gb": round(used / (1024 ** 3), 2),
                "free_gb": round(free / (1024 ** 3), 2),
                "percent": round(percent, 1),
            }
        except OSError as e:
            result[path] = {"error": str(e)}

    return result


# =============================================================================
# 0x3 — Suricata Process Status
# =============================================================================

def get_suricata_status(process_name: str) -> dict:
    """
    Checks whether Suricata is running and collects its process info.

    Uses 'pgrep' to find the process, then reads /proc/<pid>/status
    for memory usage details.

    Parameters
    ----------
    process_name : str
        The process name to search for (typically "suricata").

    Returns
    -------
    dict
        {
            "running": bool,
            "pid": int or null,
            "memory_rss_mb": float or null  — Resident Set Size in MB
        }

    What is RSS (Resident Set Size)?
        The amount of physical RAM the process is actually using right now.
        This is the most meaningful memory metric for "how much RAM is
        Suricata consuming on my 2 GB Pi?"
    """
    try:
        # pgrep returns the PID(s) of matching processes
        result = subprocess.run(
            ["pgrep", "-f", process_name],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return {"running": False, "pid": None, "memory_rss_mb": None}

        # Take the first PID if multiple exist
        pid = int(result.stdout.strip().split("\n")[0])

        # Read RSS from /proc/<pid>/status
        rss_kb = 0
        proc_status_path = f"/proc/{pid}/status"
        if os.path.exists(proc_status_path):
            with open(proc_status_path, "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        rss_kb = int(line.split()[1])
                        break

        return {
            "running": True,
            "pid": pid,
            "memory_rss_mb": round(rss_kb / 1024, 1),
        }

    except (subprocess.TimeoutExpired, ValueError, OSError) as e:
        return {"running": False, "pid": None, "memory_rss_mb": None, "error": str(e)}


# =============================================================================
# 0x4 — Network Interface Status
# =============================================================================

def get_interface_status(monitoring_iface: str, management_iface: str) -> dict:
    """
    Checks the status of the monitoring and management network interfaces.

    Parameters
    ----------
    monitoring_iface : str
        The passive monitoring interface (e.g., "eth0").
    management_iface : str
        The management interface (e.g., "wlan0").

    Returns
    -------
    dict
        {
            "monitoring": {
                "name": str,
                "up": bool,
                "promiscuous": bool  — critical: must be True for capture
            },
            "management": {
                "name": str,
                "up": bool,
                "ip_address": str or null
            }
        }

    How promiscuous mode detection works:
        /sys/class/net/<iface>/flags contains the interface flags as a hex
        number. Bit 8 (0x100) is the IFF_PROMISC flag. If this bit is set,
        the interface is in promiscuous mode. We check with a bitwise AND.
    """
    result = {}

    # --- Monitoring interface (eth0) ---
    mon_flags_path = f"/sys/class/net/{monitoring_iface}/flags"
    mon_operstate_path = f"/sys/class/net/{monitoring_iface}/operstate"

    mon_up = False
    mon_promisc = False

    try:
        with open(mon_operstate_path, "r") as f:
            mon_up = f.read().strip() == "up"
    except FileNotFoundError:
        pass

    try:
        with open(mon_flags_path, "r") as f:
            flags = int(f.read().strip(), 16)
            # IFF_PROMISC = 0x100 (bit 8)
            mon_promisc = bool(flags & 0x100)
    except (FileNotFoundError, ValueError):
        pass

    result["monitoring"] = {
        "name": monitoring_iface,
        "up": mon_up,
        "promiscuous": mon_promisc,
    }

    # --- Management interface (wlan0) ---
    mgmt_operstate_path = f"/sys/class/net/{management_iface}/operstate"
    mgmt_up = False
    mgmt_ip = None

    try:
        with open(mgmt_operstate_path, "r") as f:
            mgmt_up = f.read().strip() == "up"
    except FileNotFoundError:
        pass

    # Get IP address via 'ip addr show' (more reliable than parsing /proc)
    try:
        ip_result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", management_iface],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if ip_result.returncode == 0 and ip_result.stdout.strip():
            # Output format: "3: wlan0  inet 10.0.0.183/24 ..."
            parts = ip_result.stdout.strip().split()
            for i, part in enumerate(parts):
                if part == "inet":
                    mgmt_ip = parts[i + 1].split("/")[0]
                    break
    except (subprocess.TimeoutExpired, OSError):
        pass

    result["management"] = {
        "name": management_iface,
        "up": mgmt_up,
        "ip_address": mgmt_ip,
    }

    return result


# =============================================================================
# 0x5 — EVE JSON File Status
# =============================================================================

def get_eve_status(eve_path: str) -> dict:
    """
    Reports on the current state of Suricata's EVE JSON log file.

    Parameters
    ----------
    eve_path : str
        Path to eve.json.

    Returns
    -------
    dict
        {
            "exists": bool,
            "size_mb": float or null,
            "last_modified": str (ISO 8601) or null,
            "age_seconds": float or null  — seconds since last write
        }

    Why 'age_seconds' matters:
        If eve.json hasn't been written to in a long time, it might mean
        Suricata stopped processing traffic — even if the process is still
        running. This catches "Suricata is alive but deaf" scenarios.
    """
    eve_file = Path(eve_path)

    if not eve_file.exists():
        return {
            "exists": False,
            "size_mb": None,
            "last_modified": None,
            "age_seconds": None,
        }

    stat = eve_file.stat()
    size_mb = stat.st_size / (1024 * 1024)
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - mtime).total_seconds()

    return {
        "exists": True,
        "size_mb": round(size_mb, 2),
        "last_modified": mtime.isoformat(),
        "age_seconds": round(age_seconds, 1),
    }


# =============================================================================
# 0x6 — System Uptime and Load Average
# =============================================================================

def get_uptime_and_load() -> dict:
    """
    Reads system uptime and load averages from /proc.

    Returns
    -------
    dict
        {
            "uptime_hours": float,
            "load_avg_1m": float,
            "load_avg_5m": float,
            "load_avg_15m": float
        }

    What is load average?
        The average number of processes waiting to run over 1, 5, and 15
        minute windows. On the Pi 4 with 4 cores, a load average of 4.0
        means all cores are fully busy. Above 4.0 means processes are
        queuing — a sign the Pi is overloaded.
    """
    # Uptime
    with open("/proc/uptime", "r") as f:
        uptime_seconds = float(f.read().split()[0])

    # Load average
    with open("/proc/loadavg", "r") as f:
        parts = f.read().split()
        load_1 = float(parts[0])
        load_5 = float(parts[1])
        load_15 = float(parts[2])

    return {
        "uptime_hours": round(uptime_seconds / 3600, 1),
        "load_avg_1m": load_1,
        "load_avg_5m": load_5,
        "load_avg_15m": load_15,
    }


# =============================================================================
# 0x7 — CPU Temperature (Pi-specific)
# =============================================================================

def get_cpu_temperature() -> dict:
    """
    Reads the Raspberry Pi's CPU temperature from the thermal zone.

    Returns
    -------
    dict
        {"celsius": float}

    Why this matters:
        The Pi 4 throttles its CPU at 80°C and shuts down at 85°C.
        If Suricata is pushing the CPU hard, temperature monitoring
        tells you if you need to add a heatsink or reduce workload.
    """
    thermal_path = "/sys/class/thermal/thermal_zone0/temp"
    try:
        with open(thermal_path, "r") as f:
            # Value is in millidegrees Celsius (e.g., 52000 = 52.0°C)
            temp_c = int(f.read().strip()) / 1000
        return {"celsius": round(temp_c, 1)}
    except (FileNotFoundError, ValueError):
        return {"celsius": None}


# =============================================================================
# 0x8 — Assemble Full Health Report
# =============================================================================

def collect_health_report(config: dict) -> dict:
    """
    Gathers all health metrics into a single JSON-serializable dictionary.

    Parameters
    ----------
    config : dict
        Full parsed configuration dictionary.

    Returns
    -------
    dict
        Complete health report payload.
    """
    health_cfg = config["health"]
    shipper_cfg = config["shipper"]
    interfaces = health_cfg["interfaces"]

    report = {
        "sensor_id": config["shared"]["sensor_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": get_cpu_usage(),
        "cpu_temperature": get_cpu_temperature(),
        "memory": get_memory_usage(),
        "disk": get_disk_usage(health_cfg["disk_paths"]),
        "uptime_and_load": get_uptime_and_load(),
        "suricata": get_suricata_status(health_cfg["suricata_process_name"]),
        "network_interfaces": get_interface_status(
            interfaces["monitoring"], interfaces["management"]
        ),
        "eve_json": get_eve_status(shipper_cfg["eve_json_path"]),
    }

    return report


# =============================================================================
# 0x9 — Report Shipping
# =============================================================================

def ship_health_report(report: dict, config: dict, logger: logging.Logger) -> bool:
    """
    Sends the health report to the Brain's health endpoint via HTTP POST.

    Returns True if the Brain accepted the report, False otherwise.
    """
    endpoint = config["health"]["brain_endpoint"]
    timeout = config["shared"]["http_timeout"]
    tls_verify = config["shared"]["tls_verify"]

    try:
        response = requests.post(
            endpoint,
            json=report,
            timeout=timeout,
            verify=tls_verify,
        )
        if response.status_code in (200, 201):
            logger.info("Health report shipped to Brain — HTTP %d", response.status_code)
            return True
        else:
            logger.warning(
                "Brain rejected health report — HTTP %d", response.status_code
            )
            return False
    except requests.ConnectionError:
        logger.warning("Brain unreachable — health report not shipped")
        return False
    except requests.Timeout:
        logger.warning("Brain request timed out")
        return False
    except requests.RequestException as e:
        logger.error("Unexpected error shipping health report: %s", e)
        return False


def write_health_fallback(report: dict, config: dict, logger: logging.Logger) -> None:
    """
    Writes the health report to a local fallback file (JSONL format).
    """
    fallback_path = Path(config["health"]["fallback_path"])
    with open(fallback_path, "a") as f:
        f.write(json.dumps(report) + "\n")
    logger.info("Health report written to fallback: %s", fallback_path)


# =============================================================================
# 0xA — Main Entry Point
# =============================================================================

def main():
    """
    Entry point for the health check agent.

    Usage:
        python3 health_check.py
        python3 health_check.py --config /path/to/config.yaml
        python3 health_check.py --print-only    (skip shipping, just print)
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="HungryHoundDog Health Check — reports sensor system health"
    )
    parser.add_argument(
        "--config",
        default="/home/alfredo/hungryhounddog/sensor/agent/config.yaml",
        help="Path to config.yaml (default: %(default)s)",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Only print the health report to stdout (do not ship to Brain)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Set up logging
    logger = setup_logging(config)

    # Collect health data
    report = collect_health_report(config)

    # Always print to stdout (human readable, indented JSON)
    print(json.dumps(report, indent=2))

    # Ship to Brain unless --print-only was specified
    if not args.print_only:
        shipped = ship_health_report(report, config, logger)
        if not shipped:
            write_health_fallback(report, config, logger)

    logger.info("Health check complete")


if __name__ == "__main__":
    main()
