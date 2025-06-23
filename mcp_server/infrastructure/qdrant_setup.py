"""
infrastructure/qdrant_setup.py

AutoCreate Qdrant collection for memory events at app startup
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from utils.logger import get_logger

logger = get_logger("jsentrix")


def safe_create_memory_collection(
    collection_name="memory_events",
    vector_size=384,
    distance=Distance.COSINE,
    host="localhost",
    port=6333,
):
    """
    Creates the memory_events collection if it doesn't exist already.
    Safe to call at app startup.
    """
    try:
        client = QdrantClient(host=host, port=port)
        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            logger.info(f"Collection '{collection_name}' already exists.")
            return
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )
        logger.info(
            f"Collection '{collection_name}' created with vector size {vector_size} and distance {distance}."
        )
    except Exception as e:
        logger.error(f"Error creating collection '{collection_name}': {e}")
