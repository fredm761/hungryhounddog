"""
Health Check Routes
===================
Provides server health and connectivity status endpoints.

Author: HungryHoundDog Team
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from opensearchpy import OpenSearch

from ingestion.api.models import HealthReport

logger = logging.getLogger(__name__)
router = APIRouter()


def get_opensearch() -> OpenSearch:
    """Dependency to get OpenSearch client."""
    from ingestion.api.main import get_opensearch_client
    return get_opensearch_client()


def get_uptime() -> float:
    """Dependency to get server uptime."""
    from ingestion.api.main import get_server_uptime
    return get_server_uptime()


@router.get("/health", response_model=HealthReport)
async def health_check(
    opensearch: OpenSearch = Depends(get_opensearch),
    uptime: float = Depends(get_uptime)
) -> HealthReport:
    """
    Get comprehensive health status of the server.
    
    Returns:
        HealthReport with detailed status information
    """
    errors = []
    opensearch_connected = False
    opensearch_health = None
    indices_count = 0
    
    # Check OpenSearch connectivity
    try:
        cluster_health = opensearch.cluster.health()
        opensearch_connected = True
        opensearch_health = cluster_health.get("status", "unknown")
        
        # Count indices
        indices = opensearch.indices.get_alias(index="*")
        indices_count = len(indices)
        
    except Exception as e:
        error_msg = f"OpenSearch connection failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    # Determine overall status
    status = "healthy" if opensearch_connected else "degraded"
    
    return HealthReport(
        status=status,
        timestamp=datetime.now(timezone.utc),
        uptime_seconds=uptime,
        opensearch_connected=opensearch_connected,
        opensearch_health=opensearch_health,
        indices_count=indices_count,
        api_version="1.0.0",
        errors=errors
    )


@router.get("/health/opensearch")
async def opensearch_health(opensearch: OpenSearch = Depends(get_opensearch)):
    """
    Get detailed OpenSearch cluster health information.
    
    Returns:
        Dictionary with cluster health status
    """
    try:
        health = opensearch.cluster.health()
        
        return {
            "connected": True,
            "cluster_name": health.get("cluster_name"),
            "status": health.get("status"),
            "nodes_total": health.get("number_of_nodes"),
            "nodes_data": health.get("number_of_data_nodes"),
            "active_shards": health.get("active_shards"),
            "initializing_shards": health.get("initializing_shards"),
            "relocating_shards": health.get("relocating_shards"),
            "unassigned_shards": health.get("unassigned_shards")
        }
    except Exception as e:
        logger.error(f"OpenSearch health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="OpenSearch cluster is unavailable"
        )


@router.get("/health/indices")
async def indices_health(opensearch: OpenSearch = Depends(get_opensearch)):
    """
    Get health status of all indices.
    
    Returns:
        Dictionary with per-index health information
    """
    try:
        indices = opensearch.cat.indices(format="json")
        
        return {
            "total_indices": len(indices),
            "indices": [
                {
                    "name": idx.get("index"),
                    "status": idx.get("status"),
                    "doc_count": int(idx.get("docs.count", 0)),
                    "deleted_docs": int(idx.get("docs.deleted", 0)),
                    "size_bytes": idx.get("store.size"),
                    "primary_shards": int(idx.get("pri", 0)),
                    "replica_shards": int(idx.get("rep", 0))
                }
                for idx in indices
            ]
        }
    except Exception as e:
        logger.error(f"Indices health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Failed to retrieve indices health"
        )


@router.get("/health/ready")
async def readiness_check(opensearch: OpenSearch = Depends(get_opensearch)):
    """
    Kubernetes-style readiness probe.
    Returns 200 if service is ready to handle requests.
    
    Returns:
        Dictionary with readiness status
    """
    try:
        opensearch.info()
        return {"ready": True}
    except Exception as e:
        logger.warning(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service not ready"
        )


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if service is alive.
    
    Returns:
        Dictionary with liveness status
    """
    return {"alive": True}
