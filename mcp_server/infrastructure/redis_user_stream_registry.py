"""
mcp_server/infrastructure/redis_user_stream_registry
"""

import os
from dotenv import load_dotenv
import redis.asyncio as redis

__all__ = ["AsyncUserStreamRegistry", "user_stream_registry"]

load_dotenv()


class AsyncUserStreamRegistry:
    """
    Async Redis-backed registry for user_id -> stream_id mapping
    Ensures only one active stream per user globally.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None
        self.key_prefix = "user_active_stream:"

    async def connect(self):
        if not self._redis:
            self._redis = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

    async def get_stream_id(self, user_id: str) -> str:
        await self.connect()
        return await self._redis.get(f"{self.key_prefix}{user_id}")

    async def set_stream_id(self, user_id: str, stream_id: str):
        await self.connect()
        await self._redis.set(f"{self.key_prefix}{user_id}", stream_id)

    async def remove_stream_id(self, user_id: str):
        await self.connect()
        await self._redis.delete(f"{self.key_prefix}{user_id}")

    async def close(self):
        if self._redis:
            await self._redis.aclose()


# Singleton instance
user_stream_registry = AsyncUserStreamRegistry()
