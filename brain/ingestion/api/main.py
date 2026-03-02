"""
HungryHoundDog Ingestion API
============================
FastAPI application for receiving, parsing, and indexing network security logs.
Handles Suricata EVE JSON, OT protocol data, and provides health monitoring.

Author: HungryHoundDog Team
Version: 1.0.0
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from opensearchpy import OpenSearch, NotFoundError
import uvicorn

from ingestion.api.routes import ingest, health
from ingestion.api.models import HealthReport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global OpenSearch client
opensearch_client: Optional[OpenSearch] = None
server_start_time: datetime = datetime.now(timezone.utc)


async def initialize_opensearch() -> OpenSearch:
    """
    Initialize OpenSearch client and create default indices.
    
    Returns:
        OpenSearch: Configured OpenSearch client
    """
    global opensearch_client
    
    try:
        opensearch_client = OpenSearch(
            hosts=[{'host': 'opensearch', 'port': 9200}],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        
        # Test connection
        info = opensearch_client.info()
        logger.info(f"OpenSearch connected: {info['version']['number']}")
        
        # Create indices with mappings
        await create_indices()
        
        return opensearch_client
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {str(e)}")
        raise


async def create_indices():
    """Create default indices for log storage if they don't exist."""
    indices = {
        'suricata-alerts': {
            'mappings': {
                'properties': {
                    'timestamp': {'type': 'date'},
                    'event_type': {'type': 'keyword'},
                    'src_ip': {'type': 'ip'},
                    'dst_ip': {'type': 'ip'},
                    'src_port': {'type': 'integer'},
                    'dst_port': {'type': 'integer'},
                    'protocol': {'type': 'keyword'},
                    'alert_message': {'type': 'text'},
                    'severity': {'type': 'keyword'},
                    'tags': {'type': 'keyword'},
                    'raw_data': {'type': 'object', 'enabled': False}
                }
            }
        },
        'network-flows': {
            'mappings': {
                'properties': {
                    'timestamp': {'type': 'date'},
                    'src_ip': {'type': 'ip'},
                    'dst_ip': {'type': 'ip'},
                    'src_port': {'type': 'integer'},
                    'dst_port': {'type': 'integer'},
                    'protocol': {'type': 'keyword'},
                    'bytes_in': {'type': 'long'},
                    'bytes_out': {'type': 'long'},
                    'packets': {'type': 'long'},
                    'duration_seconds': {'type': 'float'},
                    'raw_data': {'type': 'object', 'enabled': False}
                }
            }
        }
    }
    
    for index_name, index_config in indices.items():
        try:
            if not opensearch_client.indices.exists(index=index_name):
                opensearch_client.indices.create(index=index_name, body=index_config)
                logger.info(f"Created index: {index_name}")
        except Exception as e:
            logger.warning(f"Index creation error for {index_name}: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Initializing HungryHoundDog Ingestion API...")
    try:
        await initialize_opensearch()
        logger.info("API startup complete")
    except Exception as e:
        logger.error(f"Failed to initialize API: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down HungryHoundDog Ingestion API...")
    if opensearch_client:
        opensearch_client.close()
    logger.info("API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="HungryHoundDog Ingestion API",
    description="Security log ingestion and indexing service for OT networks",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router, prefix="/api", tags=["ingestion"])
app.include_router(health.router, prefix="/api", tags=["health"])


@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "HungryHoundDog Ingestion API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_opensearch_client() -> OpenSearch:
    """
    Get the global OpenSearch client.
    
    Returns:
        OpenSearch: Global OpenSearch client
        
    Raises:
        RuntimeError: If OpenSearch client is not initialized
    """
    if opensearch_client is None:
        raise RuntimeError("OpenSearch client not initialized")
    return opensearch_client


def get_server_uptime() -> float:
    """
    Get server uptime in seconds.
    
    Returns:
        float: Seconds since server started
    """
    return (datetime.now(timezone.utc) - server_start_time).total_seconds()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
