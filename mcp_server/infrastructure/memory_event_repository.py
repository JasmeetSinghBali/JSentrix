"""
infrastructure/memory_event_repository.py

Async-optimized Qdrant repository using native async client and FastEmbed.
"""

from typing import List, Optional, Dict, Any, Tuple
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client.http.models import PointStruct
from domain.models import MemoryEvent
from utils.qdrant_utils import get_async_qdrant_client
from utils.embedding_utils import get_langchain_embedding_model
from utils.logger import get_logger
import anyio

logger = get_logger("memory_event_repository")

COLLECTION_NAME = "memory_events"


class MemoryEventRepository:
    """
    Async-native repository for MemoryEvent storage/retrieval in Qdrant.
    Uses native async client with FastEmbed for high performance.
    """

    def __init__(
        self, vector_size: int = 384, host: str = "localhost", port: int = 6333
    ):
        self.client = get_async_qdrant_client(host=host, port=port)
        self.vector_size = vector_size
        self.embedding_model = get_langchain_embedding_model()

    async def store(self, event: MemoryEvent, vector: List[float]) -> None:
        """
        Async store with connection pooling and batch-ready design.

        Args:
            event (MemoryEvent): The event to store.
            vector (List[float]): The embedding vector.
        """
        point = PointStruct(
            id=event.event_id,
            vector=vector,
            payload=event.model_dump(),
        )
        await self.client.upsert(
            collection_name=COLLECTION_NAME, points=[point], wait=True
        )

    async def query(
        self,
        query_vector: Optional[List[float]] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        offset: Optional[Any] = None,
    ) -> Tuple[List[MemoryEvent], Optional[Any]]:
        """
        Async-native query with proper connection handling and error recovery.

        Args:
            query_vector: Vector to search by (optional).
            top_k: Number of results to return.
            filters: Metadata filters (optional).
            offset: Pagination offset (optional).

        Returns:
            Tuple of (list of MemoryEvent, next offset).
        """
        qdrant_filter = self._build_filter(filters)
        try:
            if query_vector is not None:
                response = await self.client.query_points(
                    collection_name=COLLECTION_NAME,
                    query=query_vector,
                    limit=top_k,
                    query_filter=qdrant_filter,
                    with_payload=True,
                    timeout=5,
                )
                # list of hits
                hits = response.points
                return [MemoryEvent.model_validate(hit.payload) for hit in hits], None
            else:
                response = await self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    scroll_filter=qdrant_filter,
                    limit=top_k,
                    offset=offset,
                    with_payload=True,
                    timeout=5,
                )
                points, next_offset = response
                return [
                    MemoryEvent.model_validate(hit.payload) for hit in points
                ], next_offset
        except Exception as e:
            logger.error(f"Qdrant query failed: {str(e)}")
            raise

    async def fetch_all_events_with_pagination(
        self,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 100,
    ) -> List[MemoryEvent]:
        """
        Async-native paginated fetch with backpressure control.

        Args:
            filters: Metadata filters (optional).
            batch_size: Number of results per page.

        Returns:
            List of MemoryEvent objects.
        """
        qdrant_filter = self._build_filter(filters)
        all_points = []
        next_offset = None

        while True:
            response = await self.client.scroll(  # Non-blocking network I/O
                collection_name=COLLECTION_NAME,
                scroll_filter=qdrant_filter,
                limit=batch_size,
                offset=next_offset,
                with_payload=True,
                timeout=10,
            )
            points, next_offset = response
            all_points.extend(points)  # Fast, but CPU work
            # 📌 Even though await client.scroll(...) is async and yields internally (good!), the loop itself is:
            # Fast enough to repeat immediately
            # And runs until all records are fetched (could be thousands)
            # This means client.scroll() coroutine might hog the event loop, even though it technically awaits inside.
            # await anyio.sleep(0) breaks that rapid loop just enough to let other tasks "breathe", like:
            # Logging, HTTP requests, Background jobs, Cleanup callbacks, WebSocket pings, Other client queries
            await anyio.sleep(
                0
            )  # 📌 await anyio.sleep(0) is way of manually inserting a yield point in a tight async loop, so the event loop can maintain fairness and responsiveness by briefly checking in on other tasks.
            if not next_offset:
                break

        return [MemoryEvent.model_validate(point.payload) for point in all_points]

    def _build_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """
        Helper for filter construction.
        """
        if not filters:
            return None
        return Filter(
            must=[
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
        )

    async def close(self) -> None:
        """
        Explicit cleanup for async client.
        """
        await self.client.close()
