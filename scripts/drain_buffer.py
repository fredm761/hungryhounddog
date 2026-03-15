#!/usr/bin/env python3
"""
HungryHoundDog — Buffer Drain Script
Reads the JSONL fallback buffer accumulated while Brain was offline,
and POSTs batches to the FastAPI ingestion endpoint.

Run this on the Sensor ONCE after the Brain's ingestion endpoint is confirmed working.

Usage:
    python3 drain_buffer.py --endpoint http://10.0.0.180:8080/ingest \
                            --buffer /tmp/hungryhounddog_buffer.jsonl \
                            --batch-size 100 \
                            --sensor-id sensor
"""

import argparse
import json
import sys
import requests


def drain(endpoint: str, buffer_path: str, batch_size: int, sensor_id: str) -> None:
    total_sent = 0
    total_errors = 0
    batch = []

    try:
        with open(buffer_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    batch.append(event)
                except json.JSONDecodeError:
                    print(f"  [WARN] Skipping malformed JSON on line {line_num}")
                    total_errors += 1
                    continue

                if len(batch) >= batch_size:
                    sent = _send_batch(endpoint, sensor_id, batch)
                    total_sent += sent
                    batch = []
                    # Progress indicator
                    if total_sent % 500 == 0:
                        print(f"  ... sent {total_sent} events so far")

        # Flush remaining
        if batch:
            sent = _send_batch(endpoint, sensor_id, batch)
            total_sent += sent

    except FileNotFoundError:
        print(f"[ERROR] Buffer file not found: {buffer_path}")
        sys.exit(1)

    print(f"\n[DONE] Drained {total_sent} events, {total_errors} parse errors")
    print(f"You can now safely delete the buffer: rm {buffer_path}")


def _send_batch(endpoint: str, sensor_id: str, events: list) -> int:
    payload = {"sensor_id": sensor_id, "events": events}
    try:
        resp = requests.post(endpoint, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return result.get("indexed", len(events))
    except requests.RequestException as e:
        print(f"  [ERROR] Failed to send batch of {len(events)}: {e}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drain the HungryHoundDog buffer file")
    parser.add_argument("--endpoint", default="http://10.0.0.180:8080/ingest")
    parser.add_argument("--buffer", default="/tmp/hungryhounddog_buffer.jsonl")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--sensor-id", default="sensor")
    args = parser.parse_args()

    print(f"[START] Draining {args.buffer} → {args.endpoint}")
    drain(args.endpoint, args.buffer, args.batch_size, args.sensor_id)
