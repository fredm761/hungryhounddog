"""
Pydantic Data Models for HungryHoundDog
========================================
Defines request/response schemas for the ingestion API.

Author: HungryHoundDog Team
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AlertData(BaseModel):
    """Suricata alert event data."""
    action: str
    gid: int
    signature_id: int
    signature: str
    category: str
    severity: int


class FlowData(BaseModel):
    """Network flow statistics."""
    bytes_in: int
    bytes_out: int
    pkts_in: int
    pkts_out: int
    start: str
    end: str
    duration: float


class SuricataEvent(BaseModel):
    """Normalized Suricata EVE JSON event."""
    timestamp: datetime
    flow_id: Optional[int] = None
    src_ip: str = Field(..., alias="src.ip")
    src_port: Optional[int] = Field(None, alias="src.port")
    dst_ip: str = Field(..., alias="dst.ip")
    dst_port: Optional[int] = Field(None, alias="dst.port")
    proto: str
    event_type: str
    alert: Optional[AlertData] = None
    flow: Optional[FlowData] = None
    http: Optional[Dict[str, Any]] = None
    dns: Optional[Dict[str, Any]] = None
    tls: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True


class FlowRecord(BaseModel):
    """Parsed network flow record."""
    timestamp: datetime
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    protocol: str
    bytes_in: int
    bytes_out: int
    packet_count: int
    duration_seconds: float
    tags: List[str] = Field(default_factory=list)


class AlertEvent(BaseModel):
    """Security alert event."""
    timestamp: datetime
    src_ip: str
    dst_ip: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: str
    alert_message: str
    severity: int
    event_type: str
    tags: List[str] = Field(default_factory=list)
    signature_id: Optional[int] = None


class IngestBatch(BaseModel):
    """Batch of log events for ingestion."""
    batch_id: str
    timestamp: datetime
    source: str
    event_count: int
    events: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    """Response from ingestion endpoint."""
    success: bool
    batch_id: str
    processed_count: int
    failed_count: int
    message: str


class HealthReport(BaseModel):
    """Server health status report."""
    status: str
    timestamp: datetime
    uptime_seconds: float
    opensearch_connected: bool
    opensearch_health: Optional[str] = None
    indices_count: int
    api_version: str
    errors: List[str] = Field(default_factory=list)
