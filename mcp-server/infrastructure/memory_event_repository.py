"""
infrastructure/memory_event_repository

MemoryEventRepository

Handles low-level Qdrant persistence for MemoryEvent domain objects.

Usage:
    from infrastructure.memory_event_repository import MemoryEventRepository
    repo = MemoryEventRepository()
    repo.store(event, vector)
    results = repo.query(query_vector, top_k=5, filters={"user_id": "alice"})
"""

from typing import List, Optional, Dict, Any
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from domain.models import MemoryEvent
from utils.qdrant_utils import get_qdrant_client
from utils.embedding_utils import get_langchain_embedding_model

COLLECTION_NAME = "memory_events"


class MemoryEventRepository:
    def __init__(
        self, vector_size: int = 384, host: str = "localhost", port: int = 6333
    ):
        self.client = get_qdrant_client(host=host, port=port)
        self.vector_size = vector_size
        self.embedding_model = get_langchain_embedding_model()

    def store(self, event: MemoryEvent, vector: List[float]) -> None:
        """
        Upsert a memory event with its vector and metadata into qdrant

        Args:
            event (MemoryEvent): event
            vector (List[float]): vector
        """
        # PointStruct core data model that represent single point domain specifc memory events in vector collection of qdrant for retrieval based vecor similarity and metadata filters
        point = PointStruct(
            id=event.event_id,
            vector=vector,
            payload=event.dict(),  # metadata dict key-value pairs
        )
        self.client.upsert(collection_name=COLLECTION_NAME, points=[point])

    def query(
        self,
        query_vector: Optional[List[float]] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEvent]:
        """
        Query Qdrant for most relevant memory events by optional vector similarity or optional metadata filters or both
        Returns a list of typed domain objects of type MemoryEvent from models
        """
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        if query_vector is not None:
            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=top_k,
                filter=qdrant_filter,
            )
        else:
            # Metadata-only: Use scroll API
            results = self.client.scroll(
                collection_name=COLLECTION_NAME, limit=top_k, filter=qdrant_filter
            )[
                0
            ]  # pagination scroll Returns a tuple: (points, next_page_offset)
        # convert dict (hit.payload) into MemoryEvent class instance JSON-like typed object
        return [MemoryEvent.parse_obj(hit.payload) for hit in results]
