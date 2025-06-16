"""
utils/qdrant_utils.py

Qdrant client factory utility.
Provides singleton QdrantClient (sync) and AsyncQdrantClient (async) for vector DB operations.

Usage:
    from utils.qdrant_utils import get_qdrant_client, get_async_qdrant_client

    # Sync client (legacy)
    client = get_qdrant_client()

    # Async client (recommended for async code)
    async_client = get_async_qdrant_client()

    reff: https://github.com/qdrant/qdrant-client?tab=readme-ov-file#async-client
    async_client.create_collection(...)
    async_client.upsert(...)
    async_client.query_points(...)

"""

from qdrant_client import QdrantClient, AsyncQdrantClient
from typing import Optional
import threading
from utils.logger import get_logger

logger = get_logger("qdrant_utils")

# --- Singleton for sync client (legacy) ---
_qdrant_client_lock = threading.Lock()
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client(host: str = "localhost", port: int = 6333) -> QdrantClient:
    """
    Returns a singleton QdrantClient connected to the specified Qdrant instance.

    Args:
        host (str): Qdrant host address.
        port (int): Qdrant port.

    Returns:
        QdrantClient: The connected client instance.
    """
    global _qdrant_client
    if _qdrant_client is None:
        with _qdrant_client_lock:
            if _qdrant_client is None:
                logger.info(f"Creating new QdrantClient at {host}:{port}")
                _qdrant_client = QdrantClient(host=host, port=port)
    return _qdrant_client


def close_qdrant_client():
    """
    Closes the Qdrant client connection if it exists.
    """
    global _qdrant_client
    if _qdrant_client is not None:
        logger.info("Closing QdrantClient connection (noop for now).")
        _qdrant_client = None


# --- Async client factory (stateless, always returns a new client) ---
def get_async_qdrant_client(
    host: str = "localhost", port: int = 6333
) -> AsyncQdrantClient:
    """
    Returns a new AsyncQdrantClient connected to the specified Qdrant instance.

    Args:
        host (str): Qdrant host address.
        port (int): Qdrant port.

    Returns:
        AsyncQdrantClient: The connected async client instance.
    """
    logger.info(f"Creating new AsyncQdrantClient at {host}:{port}")
    return AsyncQdrantClient(
        host=host,
        port=port,
        timeout=10.0,
        prefer_grpc=True,  # Best performance for async
    )
