"""
mcp_server/infrastructure/redis_streams.py

Robust Redis Streams client using asyncio.
- Producer: Add events to stream (ex-assessment agent)
- Consumer: Read/process events using consumer groups (ex-action agent)
- Scalable: Multiple agents can consume in parallel
- Reliable: At-least-once delivery, pending message recovery
- Async and connection pooled

Usage:
    # Producer (assessment agent)
    from mcp_server.infrastructure.redis_streams import RedisStreams

    async def assess_and_push(event):
        redis_streams = RedisStreams()
        await redis_streams.produce("assessed_events_stream", {
            "event_id": event["id"],
            "action_required": True,
            "metadata": {...}
        })

    # Consumer (action agent)
    # 📌 NOTE- better to use via the mcp_server/workers/assessed_events_stream_worker.py per action agent instance
    from mcp_server.infrastructure.redis_streams import RedisStreams

    async def process_events():
        redis_streams = RedisStreams()
        async for msg_id, data in redis_streams.consume(
            stream="assessed_events_stream",
            group="action_agents",
            consumer="action_agent_1"
        ):
            await take_action(data)
            await redis_streams.ack("assessed_events_stream", "action_agents", msg_id)

"""

import asyncio
import json
import os
import redis.asyncio as redis
from typing import AsyncGenerator, Optional, Any, Dict, Tuple
from redis.exceptions import RedisError, ConnectionError
from utils.logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("redis_streams.mcpserver")


class RedisStreams:
    """
    Asyncio-based Redis streams client for scalable reliable event processing
    """

    def __init__(self, redis_url: Optional[str] = None, max_connections: int = 100):
        """
        Initialize Redis Pub/Sub client

        Args:
            redis_url: Redis connection URL
            max_connections: Connection pool size
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.max_connections = max_connections
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """
        Establish Redis connection with connection pooling
        """
        if not self._redis:
            try:
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=self.max_connections,
                    socket_keepalive=True,
                )
                await self._redis.ping()
                logger.info(
                    f"[RedisStreams.MCPServer] Connected to Redis at {self.redis_url}"
                )
            except (ConnectionError, RedisError) as e:
                logger.error(f"[RedisStreams.MCPServer] Redis connection failed: {e}")
                raise

    async def produce(self, stream: str, data: Dict[str, Any]) -> str:
        """
        Add an event to the Redis stream

        Args:
            stream: Stream name
            data: Dictionary (will be JSON-encoded per field)

        Returns:
            Message ID
        """
        await self.connect()
        try:
            # store each value as json string for type safety
            encoded = {k: json.dumps(v) for k, v in data.items()}
            msg_id = await self._redis.xadd(stream, encoded)
            logger.debug(
                f"[RedisStreams.MCPServer] Produced event to '{stream}' with ID {msg_id} "
            )
            return msg_id
        except RedisError as e:
            logger.error(f"[RedisStreams.MCPServer] Produce error: {e}")
            raise

    async def create_consumer_group(self, stream: str, group: str) -> None:
        """
        Create a redis stream consumer group if it doesnt exist
        """
        await self.connect()
        try:
            # create stream and grp if not exist
            await self._redis.xgroup_create(
                stream,
                group,
                # use $ if need to start reading messages added after this point only i.e no existing backlog
                id="0",  # "0" group consumers begins reading on first creation i.e starts from the very beginning of the stream
                mkstream=True,  # makes sure that stream exists if not creates empty one before creating the group
            )
            logger.info(
                f"[RedisStreams.MCPServer] Created consumer group '{group}' on '{stream}' "
            )
        except RedisError as e:
            if "BUSYGROUP" in str(e):
                # Group already exist
                logger.info(
                    f"[RedisStreams.MCPServer] Consumer group '{group}' already exists on '{stream}' "
                )
            else:
                logger.error(f"[RedisStreams.MCPServer] Group creation error: {e}")
                raise

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        block: int = 5000,
        count: int = 10,
        auto_ack: bool = False,
        noack: bool = False,
        start_id: str = ">",
    ) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
        """
        Consume events from the Redis stream as part of a consumer group

        Args:
            stream: Stream name
            group: Consumer group name
            consumer: Consumer name (unique per agent instance)
            block: Block time in ms (wait for new messages)
            count: Max messages per batch
            auto_ack: If True, acknowledge messages automatically
            noack: If True, disables pending tracking (at-most-once)
            start_id: Stream ID to start from (default: ">" for new messages)

        Yields:
            (message_id, data_dict)
        """
        await self.connect()
        while True:
            try:
                response = await self._redis.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={stream: start_id},
                    count=count,
                    block=block,
                    noack=noack,
                )

                if response:
                    for stream_name, messages in response:
                        for msg_id, fields in messages:
                            try:
                                # decoding JSON fields
                                decoded = {k: json.loads(v) for k, v in fields.items()}
                                yield msg_id, decoded
                                if auto_ack:
                                    await self.ack(stream, group, msg_id)
                            except Exception as e:
                                logger.error(
                                    f"[RedisStreams.MCPServer] Message decode error: {e}"
                                )
                else:
                    await asyncio.sleep(0.01)  # prevent tight loop blocking when idle
            except asyncio.CancelledError:
                logger.info("[RedisStreams.MCPServer] Consumer cancelled.")
                break
            except (ConnectionError, RedisError) as e:
                logger.error(f"[RedisStreams.MCPServer] Consume error: {e}")
                await asyncio.sleep(1)  # Backoff on error

    async def ack(self, stream: str, group: str, msg_id: str) -> None:
        """
        Acknowledge a msg as processed
        """
        await self.connect()
        try:
            await self._redis.xack(stream, group, msg_id)
            logger.debug(
                f"[RedisStreams.MCPServer] Acknowledged msg {msg_id} in group '{group}' "
            )
        except RedisError as e:
            logger.error(f"[RedisStreams.MCPServer] Ack error: {e}")

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            logger.info("[RedisPubSub.MCPServer] Redis connection closed")
