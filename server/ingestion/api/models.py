"""
HungryHoundDog — Pydantic Data Models
Defines the request/response shapes for the ingestion API.
"""

from pydantic import BaseModel


class IngestBatch(BaseModel):
    """
    Batch of Suricata EVE JSON events sent by the log shipper.

    The shipper POSTs a JSON object with:
      - sensor_id: which sensor sent this batch
      - events: list of raw EVE JSON dicts (variable structure per event_type)
    """
    sensor_id: str
    events: list[dict]


class IngestResponse(BaseModel):
    """Response after a successful ingest."""
    status: str
    indexed: int
    errors: int


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""
    status: str
    opensearch: str
    version: str


class SensorHealthReport(BaseModel):
    """
    Health report sent by the sensor's health_check.py agent.
    We accept it as a flexible dict since the sensor defines the shape.
    """
    sensor_id: str
    report: dict
