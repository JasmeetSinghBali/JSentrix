"""
application/retrievers/memory_event_retriever

MemoryEventRetriever

Supports flexible audit/history queries for user, session, agent, or any metadata,
with optional vector similarity for context-aware retrieval.

Usage in Triage Flow or Agent:
    retriever = MemoryEventRetriever(repo)
    # Hybrid: vector+metadata
    events = retriever.get_events(
        query_vector=embedding,
        filters={"user_id": "alice"},
        top_k=10
    )
    # Metadata-only
    events = retriever.get_events(filters={"user_id": "alice"}, top_k=100)
    # Vector-only
    events = retriever.get_events(query_vector=embedding, top_k=10)

    # Async usage:
    events = await retriever.async_get_events(query_vector=embedding, filters=..., top_k=10)
"""

from typing import List, Optional, Dict, Any
from domain.models import MemoryEvent
from infrastructure.memory_event_repository import MemoryEventRepository


class MemoryEventRetriever:
    """
    Retrieves memory events using hybrid (vector+metadata), metadata-only, or vector-only queries.
    Supports both synchronous and asynchronous usage.
    """

    def __init__(self, repository: MemoryEventRepository):
        self.repository = repository

    def get_events(
        self,
        query_vector: Optional[List[float]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 100,
    ) -> List[MemoryEvent]:
        """
        Retrieve memory events using vector similarity, metadata filters, or both.

        Args:
            query_vector: Optional vector for similarity search (None = metadata-only).
            filters: Optional metadata filter dict (None = vector-only).
            top_k: Max results.

        Returns:
            List[MemoryEvent]
        """
        # If neither vector nor filter is provided, raise error (ambiguous)
        if query_vector is None and filters is None:
            raise ValueError("Must provide at least one of query_vector or filters.")

        events, _ = self.repository.query(
            query_vector=query_vector, top_k=top_k, filters=filters
        )

        return events

    async def async_get_events(
        self,
        query_vector: Optional[List[float]] = None,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 100,
    ) -> List[MemoryEvent]:
        """
        Asynchronously retrieve memory events using vector similarity, metadata filters, or both.

        Args:
            query_vector: Optional vector for similarity search (None = metadata-only).
            filters: Optional metadata filter dict (None = vector-only).
            top_k: Max results.

        Returns:
            List[MemoryEvent]
        """
        if query_vector is None and filters is None:
            raise ValueError("Must provide at least one of query_vector or filters.")

        events, _ = await self.repository.async_query(
            query_vector=query_vector, top_k=top_k, filters=filters
        )
        return events
