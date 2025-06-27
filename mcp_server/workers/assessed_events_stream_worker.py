"""
mcp_server/workers/assessed_events_stream_worker.py

Async Redis Streams consumer worker for yielding assessed events to the action agent.

Features:
- Uses Redis Streams consumer groups for scalable, at-least-once delivery.
- Designed to be started and managed directly by each action agent instance.
- Handles graceful shutdown and resource cleanup.
- Each action agent instance should use a unique consumer name.
- Yields (msg_id, data) tuples for the agent to process and ack.

Usage Example (inside action agent):

    import asyncio
    import uuid
    from mcp_server.workers.assessed_events_stream_worker import assessed_events_consumer_worker
    from mcp_server.infrastructure.redis_streams import RedisStreams

    consumer_name = f"action_agent_{uuid.uuid4()}"
    redis_streams = RedisStreams()

    async for msg_id, data in assessed_events_consumer_worker(
        consumer=consumer_name,
        redis_streams=redis_streams
    ):
        await take_action(data) # processing assessed events in agent_action method
        await redis_streams.ack("assessed_events_stream", "action_agents", msg_id)

    # On shutdown (if not handled in finally):
    await redis_streams.close()


Environment Variables (optional, with defaults):
    ASSESSED_EVENTS_STREAM   - Redis stream name (default: "assessed_events_stream")
    ASSESSED_EVENTS_GROUP    - Consumer group name (default: "action_agents")
    ASSESSED_EVENTS_CONSUMER - Consumer name (default: "action_agent_<pid>")
"""

import asyncio
import os
from mcp_server.infrastructure.redis_streams import RedisStreams
from utils.logger import get_logger

logger = get_logger("assessed_events_stream_worker")

STREAM_NAME = os.getenv("ASSESSED_EVENTS_STREAM", "assessed_events_stream")
CONSUMER_GROUP = os.getenv("ASSESSED_EVENTS_GROUP", "action_agents")
CONSUMER_NAME = os.getenv("ASSESSED_EVENTS_CONSUMER", f"action_agent_{os.getpid()}")

async def assessed_events_consumer_worker(
    stream: str = STREAM_NAME,
    group: str = CONSUMER_GROUP,
    consumer: str = CONSUMER_NAME,
    redis_streams: RedisStreams = None,
):
    """
    Async generator that yields (msg_id, data) from the Redis stream.
    The action agent is responsible for processing and acknowledging each message.

    Yields:
        msg_id (str): The Redis Stream message ID.
        data (dict): The event data.
    """
    close_on_exit = False
    if redis_streams is None:
        redis_streams = RedisStreams()
        close_on_exit = True

    await redis_streams.create_consumer_group(stream, group)
    logger.info(f"Worker started: stream={stream}, group={group}, consumer={consumer}")

    try:
        async for msg_id, data in redis_streams.consume(
            stream=stream,
            group=group,
            consumer=consumer,
            block=5000,
            count=10,
            auto_ack=False
        ):
            # async def -> yield pattern as checkoint,pause
            # 📌 asynchronous generator 
            #  generator pauses and gives control to event_loop for running other coroutines and task waiting for next iteration
            # only when new message arrives the generator resumes yield the value and then pause again until the next message
            yield msg_id, data
    except Exception as e:
        logger.error(f"Unhandled error in worker: {e}")
    finally:
        if close_on_exit:
            logger.info("Shutting down RedisStreams connection...")
            await redis_streams.close()
