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

from typing import List, Optional, Dict, Any, Tuple
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from domain.models import MemoryEvent
from utils.qdrant_utils import get_qdrant_client
from utils.embedding_utils import get_langchain_embedding_model
from utils.logger import get_logger

logger = get_logger("jsentrix")

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
            payload=event.model_dump(),  # metadata dict key-value pairs
        )
        self.client.upsert(collection_name=COLLECTION_NAME, points=[point])

    def query(
        self,
        query_vector: Optional[List[float]] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        offset: Optional[Any] = None,
    ) -> Tuple[List[MemoryEvent], Optional[Any]]:
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
            response = self.client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=top_k,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False,
            )
            points = response.points
            logger.info(f"DEBUG: points type: {type(points)}")
            logger.info(f"DEBUG: points value: {points}")
            return [MemoryEvent.model_validate(hit.payload) for hit in points], None
        else:
            # reff: https://qdrant.tech/documentation/concepts/filtering/
            # The .scroll() method returns a tuple:
            # The first element is a list of points (each with .payload, .id, etc.).
            # The second element is the next page offset (used for pagination).
            # Metadata-only: Use scroll API
            # unpack the tuple from scroll
            points, next_offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=qdrant_filter,
                limit=top_k,
                offset=offset,  # Pass offset for pagination
                with_payload=True,
                with_vectors=False,
            )
            return [
                MemoryEvent.model_validate(hit.payload) for hit in points
            ], next_offset

    def fetch_all_events_with_pagination(
        self,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
    ) -> List[MemoryEvent]:
        """
        Retrieve all MemoryEvent objects from Qdrant using pagination via scroll.

        Args:
            filters: Dict of metadata filters (optional).
            batch_size: Number of points per page.

        Returns:
            List of MemoryEvent objects matching the filter.

        Usage:
            repo = MemoryEventRepository()
            all_events = repo.fetch_all_events_with_pagination(filters={"user_id": "alice"}, batch_size=200)
        """
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        all_points = []
        next_offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=qdrant_filter,
                limit=batch_size,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            all_points.extend(points)
            if not next_offset:
                break  # No more pages

        # Convert to MemoryEvent objects
        return [MemoryEvent.model_validate(point.payload) for point in all_points]
