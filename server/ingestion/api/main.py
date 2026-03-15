"""
HungryHoundDog — FastAPI Log Ingestion Service
Receives Suricata EVE JSON events from the Sensor's log shipper,
indexes them into OpenSearch with daily index rotation.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from opensearchpy import OpenSearch

from api.db import set_os_client
from api.routes.ingest import router as ingest_router
from api.routes.health import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hhd.ingestion")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle: connect to OpenSearch, create index template."""
    import os

    host = os.environ.get("OPENSEARCH_HOST", "opensearch")
    port = int(os.environ.get("OPENSEARCH_PORT", "9200"))

    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        use_ssl=False,
        verify_certs=False,
        timeout=30,
    )

    # Store in the shared module
    set_os_client(client)

    # Verify connectivity
    info = client.info()
    logger.info(
        "Connected to OpenSearch %s (cluster: %s)",
        info["version"]["number"],
        info["cluster_name"],
    )

    # Create an index template so every daily index gets the right settings
    _create_index_template(client)

    yield  # App runs here

    client.close()
    logger.info("OpenSearch connection closed")


def _create_index_template(client: OpenSearch) -> None:
    import os

    prefix = os.environ.get("INDEX_PREFIX", "hungryhounddog-events")

    template_body = {
        "index_patterns": [f"{prefix}-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s",
            },
            "mappings": {
                "dynamic": True,
                "properties": {
                    "timestamp": {"type": "date"},
                    "event_type": {"type": "keyword"},
                    "src_ip": {"type": "ip"},
                    "dest_ip": {"type": "ip"},
                    "src_port": {"type": "integer"},
                    "dest_port": {"type": "integer"},
                    "proto": {"type": "keyword"},
                    "community_id": {"type": "keyword"},
                    "sensor_id": {"type": "keyword"},
                    "app_proto": {"type": "keyword"},
                    "alert": {
                        "properties": {
                            "signature": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                            "signature_id": {"type": "long"},
                            "severity": {"type": "integer"},
                            "category": {"type": "keyword"},
                            "action": {"type": "keyword"},
                            "rev": {"type": "integer"},
                            "gid": {"type": "integer"},
                        }
                    },
                    "flow": {
                        "properties": {
                            "bytes_toserver": {"type": "long"},
                            "bytes_toclient": {"type": "long"},
                            "pkts_toserver": {"type": "long"},
                            "pkts_toclient": {"type": "long"},
                            "start": {"type": "date"},
                            "end": {"type": "date"},
                            "state": {"type": "keyword"},
                            "reason": {"type": "keyword"},
                        }
                    },
                    "flow_id": {"type": "long"},
                    "in_iface": {"type": "keyword"},
                },
            },
        },
    }

    client.indices.put_index_template(
        name="hungryhounddog-events",
        body=template_body,
    )
    logger.info("Index template 'hungryhounddog-events' created/updated")


# --- App creation ---
app = FastAPI(
    title="HungryHoundDog Ingestion API",
    description="Receives Suricata EVE JSON logs from sensors and indexes them into OpenSearch.",
    version="0.3.0",
    lifespan=lifespan,
)

app.include_router(ingest_router)
app.include_router(health_router)
