"""
infrastructure/qdrant_setup.py

Create Qdrant collection for memory events

Usage:
    python -m infrastructure.qdrant_setup
    onsuccess below shud get logged
    Collection 'memory_events' created with vector size 384 and distance Cosine.

    go to http://localhost:6333/dashboard
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from utils.logger import get_logger

logger = get_logger("jsentrix")


def create_memory_event_collection(
    collection_name="memory_events",
    vector_size=384,  # Set to your embedding dimension
    distance=Distance.COSINE,
    host="localhost",
    port=6333,
):
    client = QdrantClient(host=host, port=port)
    if collection_name in [c.name for c in client.get_collections().collections]:
        logger.info(f"Collection '{collection_name}' already exists.")
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=distance),
    )
    logger.info(
        f"Collection '{collection_name}' created with vector size {vector_size} and distance {distance}."
    )


if __name__ == "__main__":
    create_memory_event_collection()
