"""
mcp_server/infrastructure/redis_stream_registry.py

AsyncStream registery to track active streaming sessions for all agents and parts in mcp_server
reff: https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
"""

import os
from dotenv import load_dotenv
import redis.asyncio as redis

__all__ = ["AsyncStreamRegistry", "active_streams_registry"]

load_dotenv()


class AsyncStreamRegistry:
    """
    Async Redis-backed registry for active streaming sessions
    Uses a Redis set to track active stream IDs
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None
        self.active_streams_key = "active_streams"

    async def connect(self):
        if not self._redis:
            self._redis = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

    async def add(self, stream_id: str):
        """
        Register a stream as active.
        """
        await self.connect()
        await self._redis.sadd(self.active_streams_key, stream_id)

    async def remove(self, stream_id: str):
        """
        Remove a stream from the active registry.
        """
        await self.connect()
        await self._redis.srem(self.active_streams_key, stream_id)

    async def is_active(self, stream_id: str) -> bool:
        """
        Check if a stream is active.
        """
        await self.connect()
        return await self._redis.sismember(self.active_streams_key, stream_id)

    async def close(self):
        if self._redis:
            await self._redis.aclose()


# Singleton registry instance
active_streams_registry = AsyncStreamRegistry()
