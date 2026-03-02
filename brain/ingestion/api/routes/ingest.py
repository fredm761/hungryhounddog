"""
Ingestion API Routes
====================
Handles log batch ingestion and processing.

Author: HungryHoundDog Team
"""

import logging
from typing import List
from datetime import datetime, timezone
import json

from fastapi import APIRouter, HTTPException, Depends
from opensearchpy import OpenSearch

from ingestion.api.models import IngestBatch, IngestResponse
from ingestion.parsers import suricata_parser, ot_parser

logger = logging.getLogger(__name__)
router = APIRouter()


def get_opensearch() -> OpenSearch:
    """Dependency to get OpenSearch client."""
    from ingestion.api.main import get_opensearch_client
    return get_opensearch_client()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_logs(
    batch: IngestBatch,
    opensearch: OpenSearch = Depends(get_opensearch)
) -> IngestResponse:
    """
    Receive and process a batch of log events.
    
    Args:
        batch: IngestBatch containing log events
        opensearch: OpenSearch client
        
    Returns:
        IngestResponse with processing results
    """
    logger.info(f"Received batch {batch.batch_id} with {batch.event_count} events from {batch.source}")
    
    processed_count = 0
    failed_count = 0
    errors = []
    
    try:
        for event in batch.events:
            try:
                # Parse event based on source
                if batch.source.lower() == "suricata":
                    parsed_events = suricata_parser.parse_event(event)
                    
                    # Apply OT-specific parsing if applicable
                    parsed_events = [ot_parser.enrich_ot_data(e) for e in parsed_events]
                    
                    # Index each parsed event
                    for parsed_event in parsed_events:
                        _index_event(opensearch, parsed_event)
                        processed_count += 1
                else:
                    logger.warning(f"Unknown source: {batch.source}")
                    failed_count += 1
                    errors.append(f"Unknown source: {batch.source}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Event processing error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
        
        message = f"Processed {processed_count} events, {failed_count} failed"
        logger.info(f"Batch {batch.batch_id} complete: {message}")
        
        return IngestResponse(
            success=(failed_count == 0),
            batch_id=batch.batch_id,
            processed_count=processed_count,
            failed_count=failed_count,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


def _index_event(opensearch: OpenSearch, event: dict) -> None:
    """
    Index a parsed event into OpenSearch.
    
    Args:
        opensearch: OpenSearch client
        event: Parsed event dictionary
    """
    try:
        event_type = event.get("event_type", "unknown")
        
        # Determine index based on event type
        if event_type == "alert":
            index_name = "suricata-alerts"
        elif event_type == "flow":
            index_name = "network-flows"
        else:
            index_name = "hungryhounddog-logs"
        
        # Add timestamp if missing
        if "timestamp" not in event:
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        opensearch.index(
            index=index_name,
            body=event
        )
        
    except Exception as e:
        logger.error(f"Failed to index event: {str(e)}", exc_info=True)
        raise


@router.get("/ingest/stats")
async def ingest_stats(opensearch: OpenSearch = Depends(get_opensearch)):
    """
    Get ingestion statistics.
    
    Returns:
        Dictionary with index counts and statistics
    """
    try:
        stats = opensearch.indices.stats()
        
        return {
            "total_docs": stats.get("_all", {}).get("total", {}).get("docs", {}).get("count", 0),
            "total_size_bytes": stats.get("_all", {}).get("total", {}).get("store", {}).get("size_in_bytes", 0),
            "indices": {
                name: {
                    "doc_count": info.get("total", {}).get("docs", {}).get("count", 0),
                    "size_bytes": info.get("total", {}).get("store", {}).get("size_in_bytes", 0)
                }
                for name, info in stats.get("indices", {}).items()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")
