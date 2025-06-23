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
from agents.intake_agent import IntakeAgent
from agents.base_agent import AgentContext, AgentInvocationError

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

# Singleton IntakeAgent instance (or inject as needed)
intake_agent = IntakeAgent()

async def streaminges(args: Dict, stream=None) -> Dict:
    """
    Starts the Intake Agent's streaming for a given stream_id.
    Only admin users can invoke(enforced at gateway).
    """
    registry = active_streams_registry
    stream_id = args.get("stream_id")
    user_id = args.get("user_id")
    source = args.get("source", "faker")

    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        await stream.send({"error": msg})
        return {"error": msg}
    
    
    await registry.add(stream_id)
    logger.info(f"Registered stream_id {stream_id} (started by user: {user_id})")
    try:
        # Start streaming in the agent (non-blocking)
        context = AgentContext(request_id=str(uuid.uuid4()), user_id=user_id, timestamp=None)
        await intake_agent.stream(
            {"stream_id": stream_id, "source": source, "registry": registry},
            context
        )
        # Optionally send an immediate ack to the client
        await stream.send({"event": "stream_started", "stream_id": stream_id, "source": source, "started_by": user_id})
        logger.info(f"Streaming started for stream_id {stream_id} by {user_id}")
        return {"done": True, "stream_id": stream_id}
    except AgentInvocationError as e:
        msg = f"Agent error: {e}"
        logger.error(msg)
        await stream.send({"error": msg})
        return {"error": msg}
    except Exception as e:
        msg = f"Unknown error: {e}"
        logger.error(msg)
        await stream.send({"error": msg})
        return {"error": msg}
    # Note: The actual event streaming is handled via Kafka and streaming-hub.

async def abortinges(args: Dict, stream=None, context=None) -> Dict:
    """
    Aborts a running Intake Agent stream by stream_id.
    Only admin users can invoke (enforced at gateway).
    """
    registry = active_streams_registry
    stream_id = args.get("stream_id")
    user_id = args.get("user_id")  # For audit/logging

    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        return {"error": msg}

    if await registry.is_active(stream_id):
        await registry.remove(stream_id)
        logger.info(f"Aborted stream {stream_id} by user {user_id}")
        # Stop the agent's streaming task
        agent_context = AgentContext(request_id=str(uuid.uuid4()), user_id=user_id, timestamp=None)
        await intake_agent.abort({"stream_id": stream_id}, agent_context)
        await stream.send({"event": "stream_aborted", "stream_id": stream_id, "aborted_by": user_id})
        return {"aborted": True, "stream_id": stream_id}
    else:
        logger.warning(f"Tried to abort non-existent stream {stream_id}")
        return {"error": "No such stream", "stream_id": stream_id}