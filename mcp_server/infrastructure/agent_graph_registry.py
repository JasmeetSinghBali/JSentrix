"""
mcp_server/infrastructure/agent_graph_registry.py

AsyncAgentGraphRegistry: Redis-backed registry for active per-stream AgentGraphs
Ensures per-client pipelines can be tracked, isolated, and gracefully shut down
"""

import os
from dotenv import load_dotenv
import redis.asyncio as redis

__all__ = ["AsyncAgentGraphRegistry", "agent_graph_registry"]

load_dotenv()


class AsyncAgentGraphRegistry:
    """
    Redis-backed registry for active per-stream AgentGraphs
    Ensures per-client pipelines can be tracked, isolated, and gracefully shut down
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None
        self.key = "active_agent_graph_streams"

    async def connect(self):
        if not self._redis:
            self._redis = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

    async def add(self, stream_id: str):
        await self.connect()
        await self._redis.sadd(self.key, stream_id)

    async def remove(self, stream_id: str):
        await self.connect()
        await self._redis.srem(self.key, stream_id)

    async def is_active(self, stream_id: str) -> bool:
        await self.connect()
        return await self._redis.sismember(self.key, stream_id)

    async def list(self) -> list[str]:
        await self.connect()
        return await self._redis.smembers(self.key)

    async def close(self):
        if self._redis:
            await self._redis.aclose()


# Instantiate shared singleton
agent_graph_registry = AsyncAgentGraphRegistry()
