"""
HungryHoundDog — Ingest Route
POST /ingest — receives batched Suricata EVE JSON events from the sensor
log shipper and bulk-indexes them into OpenSearch with daily index rotation.
"""

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from opensearchpy.helpers import bulk

from api.main import get_os_client
from api.models import IngestBatch, IngestResponse

logger = logging.getLogger("hhd.ingest")
router = APIRouter()

INDEX_PREFIX = os.environ.get("INDEX_PREFIX", "hungryhounddog-events")


def _today_index() -> str:
    """Return today's index name, e.g. hungryhounddog-events-2026.03.15"""
    return f"{INDEX_PREFIX}-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"


def _prepare_actions(batch: IngestBatch) -> list[dict]:
    """
    Convert a batch of raw EVE JSON events into OpenSearch bulk actions.

    Each EVE JSON event has a 'timestamp' field from Suricata. We keep it
    as-is (OpenSearch maps it as a date). We also inject sensor_id so every
    document is traceable to its source sensor.
    """
    index_name = _today_index()
    actions = []

    for event in batch.events:
        # Inject sensor_id into every document
        event["sensor_id"] = batch.sensor_id

        actions.append({
            "_index": index_name,
            "_source": event,
        })

    return actions


@router.post("/ingest", response_model=IngestResponse)
async def ingest_events(batch: IngestBatch):
    """
    Receive a batch of Suricata EVE JSON events and index them into OpenSearch.

    Expected payload:
    {
        "sensor_id": "sensor",
        "events": [ { ...eve json... }, { ...eve json... }, ... ]
    }
    """
    if not batch.events:
        return IngestResponse(status="ok", indexed=0, errors=0)

    client = get_os_client()
    actions = _prepare_actions(batch)

    try:
        success_count, errors = bulk(
            client,
            actions,
            raise_on_error=False,
            raise_on_exception=False,
        )

        error_count = len(errors) if isinstance(errors, list) else 0

        if error_count > 0:
            # Log first few errors for debugging, don't spam
            for err in errors[:3]:
                logger.warning("Bulk index error: %s", err)

        logger.info(
            "Indexed %d events (%d errors) from sensor '%s' into %s",
            success_count,
            error_count,
            batch.sensor_id,
            _today_index(),
        )

        return IngestResponse(
            status="ok",
            indexed=success_count,
            errors=error_count,
        )

    except Exception as e:
        logger.error("Bulk indexing failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")
