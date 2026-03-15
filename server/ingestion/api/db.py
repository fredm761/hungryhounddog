"""
HungryHoundDog — OpenSearch Client Singleton
Broken out from main.py to avoid circular imports.
"""

from opensearchpy import OpenSearch

_client: OpenSearch | None = None


def get_os_client() -> OpenSearch:
    """Return the OpenSearch client. Called by route handlers."""
    if _client is None:
        raise RuntimeError("OpenSearch client not initialized")
    return _client


def set_os_client(client: OpenSearch) -> None:
    """Set the OpenSearch client. Called during app startup."""
    global _client
    _client = client
