"""
utils/qdrant_utils.py

Qdrant client factory utility.
Provides a singleton QdrantClient for vector DB operations.

Usage:
    from utils.qdrant_utils import get_qdrant_client

    client = get_qdrant_client()
    # Use client for upsert/query/scroll/etc.
"""

from qdrant_client import QdrantClient
from typing import Optional
import threading

from utils.logger import get_logger

logger = get_logger("qdrant_client")

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
        # to make sure one client created at a time incase multi-threaded fastapi context with workers>1
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
