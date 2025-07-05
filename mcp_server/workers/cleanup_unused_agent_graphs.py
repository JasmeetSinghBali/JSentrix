"""
mcp_server/workers/cleanup_unused_agent_graphs.py

Background worker for periodically cleaning up unused agent graphs from memory.
- Removes graphs not active in either the stream registry or agent graph registry.
- Runs as an async background task with graceful shutdown support.
"""

import asyncio
from infrastructure.agent_graph_registry import agent_graph_registry
from infrastructure.redis_stream_registry import active_streams_registry
from infrastructure.agent_graphs_store import agent_graphs
from utils.logger import get_logger
from utils.background_worker import background_worker

logger = get_logger("cleanup.agentgraphs.worker")

_CLEANUP_TASK = None
_CLEANUP_INTERVAL = 30  # seconds

@background_worker(name="AgentGraphCleanup", retry=True)
async def cleanup_unused_graphs():
    while True:
        try:
            stale_ids = []
            # Snapshot keys to avoid mutation during iteration
            for stream_id in list(agent_graphs.keys()):
                # Check both registries in parallel for efficiency
                active, registered = await asyncio.gather(
                    active_streams_registry.is_active(stream_id),
                    agent_graph_registry.is_active(stream_id)
                )
                if not active and not registered:
                    agent_graphs.pop(stream_id, None)
                    stale_ids.append(stream_id)
            if stale_ids:
                logger.info(f"🧹 Cleaned up stale agent graphs: {stale_ids}")
        except Exception as e:
            logger.exception(f"❗ Error in agent graph cleanup: {e}")
        await asyncio.sleep(_CLEANUP_INTERVAL)