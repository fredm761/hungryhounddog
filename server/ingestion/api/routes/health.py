"""
HungryHoundDog — Health Routes
GET  /health         — server health check (is the API + OpenSearch alive?)
POST /health/sensor  — receives health reports from sensor agents
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.db import get_os_client
from api.models import HealthResponse, SensorHealthReport

logger = logging.getLogger("hhd.health")
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def server_health():
    """Check if the ingestion service and OpenSearch are healthy."""
    try:
        client = get_os_client()
        info = client.info()
        return HealthResponse(
            status="healthy",
            opensearch="connected",
            version=info["version"]["number"],
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Unhealthy: {e}")


@router.post("/health/sensor")
async def receive_sensor_health(report: SensorHealthReport):
    """
    Receive a health report from a sensor's health_check.py agent.
    Indexes it into OpenSearch for monitoring and dashboarding.
    """
    client = get_os_client()

    doc = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": "sensor_health",
        "sensor_id": report.sensor_id,
        **report.report,
    }

    index_name = f"hungryhounddog-health-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"

    try:
        client.index(index=index_name, body=doc)
        logger.info("Stored health report from sensor '%s'", report.sensor_id)
        return {"status": "ok", "sensor_id": report.sensor_id}
    except Exception as e:
        logger.error("Failed to index sensor health: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to store health report: {e}")
