"""
mcp_server/tools/streaming_tools

streaminges and abortinges tool  start/abort streaming for individual clients (per stream_id)
Each stream spawns a dedicated agent graph for isolation and parallelism
Intake → Assessment → Action
"""

import uuid
from typing import Any, Dict

from domain.config_models import StreamingConfig

from utils.logger import get_logger
from utils.lifecycle import register_shutdown_callback

from infrastructure.redis_stream_registry import active_streams_registry
from infrastructure.agent_graph_registry import agent_graph_registry
from infrastructure.agent_graphs_store import agent_graphs
from infrastructure.redis_user_stream_registry import user_stream_registry

from agents.base_agent import AgentContext, AgentInvocationError
from agents.agent_graph import AgentGraph


logger = get_logger("mcp.streaming_tools")


# Register the async close method for shutdown
register_shutdown_callback(active_streams_registry.close)
# singelton registry instance for all agent graphs
register_shutdown_callback(agent_graph_registry.close)
register_shutdown_callback(user_stream_registry.close)


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



async def streaminges(args: Dict, stream=None) -> Dict:
    """
    Starts streaming for a given stream_id using a dedicated AgentGraph.
    Ensures agent isolation, stream-level config, and Redis tracking.

    Only admin users can invoke(enforced at gateway).
    """
    stream_id = args.get("stream_id")
    user_id = args.get("user_id")
    source = args.get("source", "faker")
    raw_config= args.get("config",{})
    # 📌 validate config passed from electron client to avoid polluted or malformed configs
    try:
        config = StreamingConfig(**raw_config).model_dump()
    except Exception as e:
        logger.warning(f"Invalid streaming config: {e}")
        config={}

    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        await stream.send({"error": msg})
        return {"error": msg}
    
    # Check for existing stream for this user in Redis
    old_stream_id = await user_stream_registry.get_stream_id(user_id)
    if old_stream_id and old_stream_id != stream_id:
        logger.warning(f"⚠️ User {user_id} already has active stream {old_stream_id}, aborting before starting new one.")
        try:
            await abortinges({"stream_id": old_stream_id, "user_id": user_id})
        except Exception as e:
            logger.error(f"Error aborting old stream {old_stream_id} for user {user_id}: {e}")

    # 📌 Register new stream in both registries-active_streams and agent_graph and user-stream_id
    # Register new stream for user in Redis
    await user_stream_registry.set_stream_id(user_id, stream_id)
    await active_streams_registry.add(stream_id)
    logger.info(f"🌊 Registered stream_id {stream_id} (started by user: {user_id})")
    await agent_graph_registry.add(stream_id)
    logger.info(f"🧠 Registered dedicated AgentGraph for stream_id: {stream_id}")

    # Create per-stream agent graph
    graph = AgentGraph(stream_id=stream_id)
    agent_graphs[stream_id] = graph
    logger.info(f"🤖 Created AgentGraph for stream_id={stream_id}")


    try:
        context = AgentContext(
            request_id=str(uuid.uuid4()), 
            user_id=user_id, 
            timestamp=None,
            config=config, # inject config into agentcontext will be passed to the agent pipeline
            registry=args.get("registry",[]), # pass registry to downstream pipeline and agents for active stream and graph registry checks or process if needed
        )
        # Start streaming in the agent (non-blocking)
        await graph.intake_agent.stream(
            {
                "stream_id": stream_id,
                "source": source,
                "registry": [active_streams_registry, agent_graph_registry],
                "config": config
            },
            context
        )
        # Optionally send an immediate ack to the client
        await stream.send({
            "event": "stream_started", 
            "stream_id": stream_id, 
            "source": source, 
            "started_by": user_id
        })
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
    # 🎈 Note: The actual event streaming is handled via Kafka and streaming-hub here this stream.send is for future use case if immediate websocket connection is between mcp_server<>gateway<>client

async def abortinges(args: Dict, stream=None, context=None) -> Dict:
    """
    Aborts a running Intake Agent stream by stream_id.
    Only admin users can invoke (enforced at gateway).
    """
    stream_id = args.get("stream_id")
    user_id = args.get("user_id")  # For audit/logging

    if not stream_id or not is_valid_stream_id(stream_id):
        msg = f"Invalid or missing stream_id: {stream_id}"
        logger.warning(msg)
        return {"error": msg}

    if await active_streams_registry.is_active(stream_id):
        # remove from active registry
        await active_streams_registry.remove(stream_id)
        await agent_graph_registry.remove(stream_id)
        logger.info(f"Aborted stream {stream_id} by user {user_id}")
        
        # Grab and abort running agent task
        graph = agent_graphs.pop(stream_id, None)
        if graph:
            agent_context = AgentContext(request_id=str(uuid.uuid4()), user_id=user_id, timestamp=None)
            # Stop the agent's streaming task
            await graph.abort(stream_id, agent_context) # centeralize call
        
        if stream_id and user_id:
            curr = await user_stream_registry.get_stream_id(user_id)
            if curr == stream_id:
                await user_stream_registry.remove_stream_id(user_id)
        
        if stream:
            await stream.send({
                "event": "stream_aborted",
                "stream_id": stream_id,
                "aborted_by": user_id,
            })
        
        return {"aborted": True, "stream_id": stream_id}

    else:
        logger.warning(f"⚠️ Tried to abort non-existent or inactive stream {stream_id}")
        return {"error": "No such stream", "stream_id": stream_id}