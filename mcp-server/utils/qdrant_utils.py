from qdrant_client import QdrantClient


# reff: https://python-client.qdrant.tech/qdrant_client
def get_qdrant_client(host="localhost", port=6333) -> QdrantClient:
    """
    Returns a QdrantClient connected to the local Qdrant instance.
    """
    return QdrantClient(host=host, port=port)
