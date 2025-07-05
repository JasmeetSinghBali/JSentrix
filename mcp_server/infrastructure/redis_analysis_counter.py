"""
mcp_server/infrastructure/redis_analysis_counter.py

Async Redis-backed registry for tracking the number of compliance analysis tasks
in progress per stream_id for ActionAgent.

This utility enables robust, distributed, and race-condition-free reference counting
for compliance analysis tasks:
    - Each stream_id gets its own counter in Redis.
    - .incr(stream_id) increments the count when a new analysis starts.
    - .decr(stream_id) decrements the count when an analysis finishes.
    - .get(stream_id) retrieves the current count.
    - .reset(stream_id) deletes the counter for cleanup.

Usage:
    from infrastructure.redis_analysis_counter import analysis_counter_registry

    await analysis_counter_registry.incr(stream_id)
    await analysis_counter_registry.decr(stream_id)
    count = await analysis_counter_registry.get(stream_id)
    await analysis_counter_registry.reset(stream_id)

This ensures the final compliance event is only emitted after all analyses are complete,
even in a distributed/multi-process deployment.
"""

import os
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()


class AsyncAnalysisCounterRegistry:
    """
    Async Redis-backed registry for per-stream compliance analysis task counting.

    Each stream_id is mapped to an integer counter in Redis:
        - .incr(stream_id): increment count when analysis starts
        - .decr(stream_id): decrement count when analysis finishes
        - .get(stream_id): get current count
        - .reset(stream_id): delete counter (cleanup)
    """

    def __init__(self, redis_url=None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None
        self.key_prefix = "action_analysis_counter:"

    async def connect(self):
        if not self._redis:
            self._redis = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

    async def incr(self, stream_id: str):
        await self.connect()
        return await self._redis.incr(f"{self.key_prefix}{stream_id}")

    async def decr(self, stream_id: str):
        await self.connect()
        return await self._redis.decr(f"{self.key_prefix}{stream_id}")

    async def get(self, stream_id: str):
        await self.connect()
        val = await self._redis.get(f"{self.key_prefix}{stream_id}")
        return int(val) if val is not None else 0

    async def reset(self, stream_id: str):
        await self.connect()
        await self._redis.delete(f"{self.key_prefix}{stream_id}")

    async def close(self):
        if self._redis:
            await self._redis.aclose()


# Singleton instance for all streams
analysis_counter_registry = AsyncAnalysisCounterRegistry()
