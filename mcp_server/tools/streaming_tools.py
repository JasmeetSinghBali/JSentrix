"""
mcp_server/tools/streaming_tools

streaminges and abortinges tool
"""
import asyncio
import uuid
from typing import Any, Dict
from utils.logger import get_logger
from infrastructure.redis_stream_registry import AsyncStreamRegistry
from utils.lifecycle import register_shutdown_callback

logger = get_logger("mcp.streaming_tools")

# Singleton registry instance
active_streams_registry = AsyncStreamRegistry()

# Register the async close method for shutdown
register_shutdown_callback(active_streams_registry.close)

def is_valid_stream_id(stream_id: Any) -> bool:
    """
    Validate if the given stream_id is a proper UUID.
    """
    try:
        uuid.UUID(str(stream_id))
        return True
    except Exception as e:
        logger.error(f"stream_id validation failed: {e}")
        return False

async def streaminges(args: Dict, stream,registry = None) -> Dict:
    """
    Streams incremental output (e.g., logs/events/processing) of the Intake Agent and other agents
    to the client (electron app) via the Go Fiber streaming microservice.

    Args:
        args (Dict): Must include a unique 'stream_id' for control.
        stream: Async stream object with .send() coroutine.

    Returns:
        Dict: {"done": True, "stream_id": ...} on completion, or {"error": ...} on failure.
    """
    registry = registry or active_streams_registry
    stream_id = args.get("stream_id")
    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        await stream.send({"error": msg})
        return {"error": msg}
    await registry.add(stream_id)
    try:
        for i in range(100):
            if not await registry.is_active(stream_id):
                logger.info(f"Stream {stream_id} aborted at iteration {i}")
                break
            log_event = {"event": "log", "stream_id": stream_id, "message": f"processing {i}"}
            logger.debug(f"Stream {stream_id} event: {log_event}")
            await stream.send(log_event)
            await asyncio.sleep(0.1)
        logger.info(f"Stream {stream_id} completed")
        return {"done": True, "stream_id": stream_id}
    finally:
        await registry.remove(stream_id)
        logger.info(f"Stream {stream_id} cleaned up")

async def abortinges(args: Dict, stream, context, registry = None) -> Dict:
    """
    Aborts a running stream/process by stream_id.
    Ensures all agents stop processing transactions and the Go Fiber microservice stops streaming.

    Args:
        args (Dict): Must include a valid 'stream_id'.
        stream: Async stream object.
        context: Additional context if needed.

    Returns:
        Dict: {"aborted": True, "stream_id": ...} on success, or {"error": ...}.
    """
    registry = registry or active_streams_registry
    stream_id = args.get("stream_id")
    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        return {"error": msg}
    if await registry.is_active(stream_id):
        await registry.remove(stream_id)
        logger.info(f"Aborted stream {stream_id}")
        return {"aborted": True, "stream_id": stream_id}
    else:
        logger.warning(f"Tried to abort non-existent stream {stream_id}")
        return {"error": "No such stream", "stream_id": stream_id}
