#!/usr/bin/env python3
"""
=============================================================================
HungryHoundDog — Log Shipper Agent
=============================================================================
Purpose:
    Continuously reads new lines from Suricata's EVE JSON log file, batches
    them, and ships them to the Brain's FastAPI ingestion endpoint over HTTPS.
    When the Brain is unreachable, events are written to a local fallback
    file so no data is lost.

How it works (high level):
    1. Open eve.json and seek to the end (we only care about NEW events).
    2. Read new lines as they appear (like 'tail -f').
    3. Accumulate lines into a batch.
    4. When the batch hits 'batch_size' OR 'flush_interval_seconds' elapses,
       send the batch to Brain via HTTP POST.
    5. If Brain is unreachable, write the batch to a local fallback file.
    6. Periodically check if eve.json was rotated (Suricata log rotation
       changes the file's inode). If rotated, reopen the new file.
    7. Persist the last-read byte position to a state file so that if the
       agent restarts, it resumes where it left off instead of re-sending
       old events or skipping new ones.

Runs on:  Raspberry Pi 4 ("The Sensor")
Location: /home/alfredo/hungryhounddog/sensor/agent/log_shipper.py
Service:  hungryhounddog-shipper.service (systemd)

Author:   Alfredo
Project:  HungryHoundDog — Weekend 2
=============================================================================
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# =============================================================================
# 0x1 — Configuration Loading
# =============================================================================

def load_config(config_path: str) -> dict:
    """
    Reads the YAML configuration file and returns it as a Python dictionary.

    Parameters
    ----------
    config_path : str
        Absolute path to config.yaml.

    Returns
    -------
    dict
        Parsed configuration dictionary.

    Raises
    ------
    FileNotFoundError
        If the config file does not exist at the given path.
    yaml.YAMLError
        If the config file contains invalid YAML syntax.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    return config


# =============================================================================
# 0x2 — Logging Setup
# =============================================================================

def setup_logging(config: dict) -> logging.Logger:
    """
    Configures Python's logging module based on the shared config settings.
    Logs go to both the console (stdout) and a log file.

    Parameters
    ----------
    config : dict
        The full parsed configuration dictionary.

    Returns
    -------
    logging.Logger
        Configured logger instance named 'log_shipper'.
    """
    shared = config["shared"]
    log_level = getattr(logging, shared["log_level"].upper(), logging.INFO)
    log_file = Path(shared["log_file"])

    # Create the log directory if it does not exist
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("log_shipper")
    logger.setLevel(log_level)

    # Formatter — includes timestamp, level, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )

    # Console handler (stdout) — useful when running manually for debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler — persistent log for troubleshooting
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# =============================================================================
# 0x3 — State Persistence
# =============================================================================
# The state file stores the last byte offset and inode of eve.json so that
# if the agent restarts, it picks up exactly where it left off.

def load_state(state_path: str) -> dict:
    """
    Loads the persisted state (byte offset and inode) from disk.

    Parameters
    ----------
    state_path : str
        Path to the JSON state file.

    Returns
    -------
    dict
        State dictionary with keys 'offset' (int) and 'inode' (int).
        Returns defaults (offset=0, inode=0) if the file does not exist
        or cannot be parsed.
    """
    default_state = {"offset": 0, "inode": 0}
    state_file = Path(state_path)

    if not state_file.exists():
        return default_state

    try:
        with open(state_file, "r") as f:
            state = json.load(f)
        return {
            "offset": state.get("offset", 0),
            "inode": state.get("inode", 0),
        }
    except (json.JSONDecodeError, KeyError):
        return default_state


def save_state(state_path: str, offset: int, inode: int) -> None:
    """
    Persists the current byte offset and inode to the state file.

    Parameters
    ----------
    state_path : str
        Path to the JSON state file.
    offset : int
        Current byte position in eve.json.
    inode : int
        Current inode number of eve.json (used to detect log rotation).
    """
    state_file = Path(state_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    with open(state_file, "w") as f:
        json.dump({"offset": offset, "inode": inode}, f)


# =============================================================================
# 0x4 — Batch Shipping
# =============================================================================

def ship_to_brain(batch: list[dict], config: dict, logger: logging.Logger) -> bool:
    """
    Sends a batch of EVE JSON events to the Brain's FastAPI ingestion
    endpoint via HTTP POST.

    The payload is a JSON object with two fields:
        - sensor_id: identifies which sensor sent the data
        - events: list of EVE JSON event dictionaries

    Parameters
    ----------
    batch : list[dict]
        List of parsed EVE JSON event dictionaries.
    config : dict
        Full parsed configuration dictionary.
    logger : logging.Logger
        Logger instance for status messages.

    Returns
    -------
    bool
        True if the Brain accepted the batch (HTTP 200/201), False otherwise.
    """
    endpoint = config["shipper"]["brain_endpoint"]
    timeout = config["shared"]["http_timeout"]
    tls_verify = config["shared"]["tls_verify"]
    sensor_id = config["shared"]["sensor_id"]

    payload = {
        "sensor_id": sensor_id,
        "batch_size": len(batch),
        "shipped_at": datetime.now(timezone.utc).isoformat(),
        "events": batch,
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
            verify=tls_verify,
        )
        if response.status_code in (200, 201):
            logger.info(
                "Shipped batch of %d events to Brain — HTTP %d",
                len(batch),
                response.status_code,
            )
            return True
        else:
            logger.warning(
                "Brain rejected batch — HTTP %d: %s",
                response.status_code,
                response.text[:200],
            )
            return False

    except requests.ConnectionError:
        logger.warning("Brain unreachable at %s — connection refused", endpoint)
        return False
    except requests.Timeout:
        logger.warning("Brain request timed out after %d seconds", timeout)
        return False
    except requests.RequestException as e:
        logger.error("Unexpected HTTP error shipping to Brain: %s", e)
        return False


def write_to_fallback(batch: list[dict], config: dict, logger: logging.Logger) -> None:
    """
    Writes a batch of events to the local fallback file (one JSON object
    per line, aka JSONL format) when the Brain is unreachable.

    This ensures zero data loss. Weekend 3's ingestion service can later
    drain this fallback file if needed.

    Parameters
    ----------
    batch : list[dict]
        List of parsed EVE JSON event dictionaries.
    config : dict
        Full parsed configuration dictionary.
    logger : logging.Logger
        Logger instance for status messages.
    """
    fallback_path = Path(config["shipper"]["fallback_path"])
    max_bytes = config["shipper"]["fallback_max_bytes"]

    # Rotate the fallback file if it exceeds the size limit
    if fallback_path.exists() and fallback_path.stat().st_size > max_bytes:
        rotated = fallback_path.with_suffix(".jsonl.old")
        fallback_path.rename(rotated)
        logger.info("Rotated fallback file to %s", rotated)

    with open(fallback_path, "a") as f:
        for event in batch:
            f.write(json.dumps(event) + "\n")

    logger.info(
        "Wrote %d events to fallback file %s", len(batch), fallback_path
    )


# =============================================================================
# 0x5 — File Watching (Tail Logic)
# =============================================================================

def get_inode(file_path: str) -> int:
    """
    Returns the inode number of a file. Used to detect log rotation.

    When Suricata rotates eve.json, it creates a new file with a new inode.
    If the inode changes, we know the file was rotated and we need to reopen.

    Parameters
    ----------
    file_path : str
        Path to the file.

    Returns
    -------
    int
        Inode number, or 0 if the file does not exist.
    """
    try:
        return os.stat(file_path).st_ino
    except FileNotFoundError:
        return 0


def tail_eve_json(config: dict, logger: logging.Logger) -> None:
    """
    Main loop: tails eve.json, batches events, and ships them.

    This function runs indefinitely until the process receives SIGTERM or
    SIGINT (Ctrl+C). It implements the following logic:

    1. Open eve.json and seek to the last known offset (or end of file on
       first run).
    2. Read all available new lines.
    3. Parse each line as JSON and add to the current batch.
    4. If batch is full (>= batch_size) OR the flush timer expired,
       ship the batch to Brain (or write to fallback on failure).
    5. Save the current file offset and inode to the state file.
    6. Sleep briefly (0.25s) to avoid busy-waiting, then repeat.
    7. Periodically check if the file inode changed (log rotation).

    Parameters
    ----------
    config : dict
        Full parsed configuration dictionary.
    logger : logging.Logger
        Logger instance.
    """
    eve_path = config["shipper"]["eve_json_path"]
    batch_size = config["shipper"]["batch_size"]
    flush_interval = config["shipper"]["flush_interval_seconds"]
    rotation_check = config["shipper"]["rotation_check_seconds"]
    state_path = config["shipper"]["state_file"]

    # Load persisted state
    state = load_state(state_path)
    current_inode = get_inode(eve_path)

    # Decide where to start reading
    # If the inode matches the saved state, resume at the saved offset.
    # If the inode differs (file was rotated or first run), start at the
    # end of the current file so we only ship NEW events going forward.
    if current_inode == state["inode"] and state["offset"] > 0:
        start_offset = state["offset"]
        logger.info(
            "Resuming from saved state — offset %d, inode %d",
            start_offset,
            current_inode,
        )
    else:
        # Seek to end of file — we do not want to re-ship old events
        start_offset = os.path.getsize(eve_path) if os.path.exists(eve_path) else 0
        logger.info(
            "Starting fresh — seeking to end of file (offset %d, inode %d)",
            start_offset,
            current_inode,
        )

    # Wait for eve.json to exist (Suricata might not be running yet)
    while not os.path.exists(eve_path):
        logger.warning("Waiting for %s to appear...", eve_path)
        time.sleep(5)

    # Open the file and seek to our starting position
    file_handle = open(eve_path, "r")
    file_handle.seek(start_offset)
    current_inode = get_inode(eve_path)

    # Initialize batch state
    batch: list[dict] = []
    last_flush_time = time.time()
    last_rotation_check = time.time()
    parse_errors = 0

    logger.info("Log shipper is running — watching %s", eve_path)

    while True:
        # --- Read new lines ---
        line = file_handle.readline()

        if line:
            line = line.strip()
            if line:
                try:
                    event = json.loads(line)
                    batch.append(event)
                except json.JSONDecodeError:
                    parse_errors += 1
                    if parse_errors <= 5:
                        logger.warning("Skipping malformed JSON line: %s", line[:100])
                    elif parse_errors == 6:
                        logger.warning("Suppressing further parse error logs")
        else:
            # No new data — sleep briefly to avoid busy-waiting
            # 0.25 seconds gives us sub-second latency for new events while
            # keeping CPU usage near zero on the Pi (critical for 2 GB RAM)
            time.sleep(0.25)

        # --- Check batch flush conditions ---
        now = time.time()
        time_since_flush = now - last_flush_time
        should_flush = (
            len(batch) >= batch_size
            or (len(batch) > 0 and time_since_flush >= flush_interval)
        )

        if should_flush:
            # Try to ship to Brain first; fall back to local file on failure
            shipped = ship_to_brain(batch, config, logger)
            if not shipped:
                write_to_fallback(batch, config, logger)

            # Save state after successful flush
            current_offset = file_handle.tell()
            save_state(state_path, current_offset, current_inode)

            # Reset batch
            batch = []
            last_flush_time = now
            parse_errors = 0

        # --- Check for log rotation ---
        if now - last_rotation_check >= rotation_check:
            new_inode = get_inode(eve_path)
            if new_inode != 0 and new_inode != current_inode:
                logger.info(
                    "Detected log rotation — inode changed from %d to %d, reopening",
                    current_inode,
                    new_inode,
                )
                file_handle.close()
                file_handle = open(eve_path, "r")
                current_inode = new_inode
                save_state(state_path, 0, current_inode)
            last_rotation_check = now


# =============================================================================
# 0x6 — Signal Handling and Main Entry Point
# =============================================================================

# Global flag for graceful shutdown
_shutdown_requested = False


def handle_shutdown(signum, frame):
    """
    Signal handler for SIGTERM and SIGINT. Sets a global flag that the
    main loop checks to exit gracefully.
    """
    global _shutdown_requested
    _shutdown_requested = True


def main():
    """
    Entry point for the log shipper agent.

    Usage:
        python3 log_shipper.py
        python3 log_shipper.py --config /path/to/config.yaml
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="HungryHoundDog Log Shipper — ships Suricata EVE JSON to Brain"
    )
    parser.add_argument(
        "--config",
        default="/home/alfredo/hungryhounddog/sensor/agent/config.yaml",
        help="Path to config.yaml (default: %(default)s)",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Set up logging
    logger = setup_logging(config)
    logger.info("=" * 60)
    logger.info("HungryHoundDog Log Shipper starting")
    logger.info("=" * 60)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Start tailing
    try:
        tail_eve_json(config, logger)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt — shutting down")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Log shipper stopped")


if __name__ == "__main__":
    main()
