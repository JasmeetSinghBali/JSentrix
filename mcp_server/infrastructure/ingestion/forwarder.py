"""
mcp_server/infrastructure/ingestion/forwarder/py

forwarder infra that handles event foward from mcp_server to client(electron) via streaming hub service in golang

Usage:
    import asyncio
    from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub

    event = {
        "event": "log",
        "message": "Agent did something",
        "stream_id": "123e4567-e89b-12d3-a456-426614174000"
    }

    async def process_agent_event(event):
        # ... other async work ...
        await forward_event_to_streaming_hub(event)

    # to forward many events
    async def forward_many(events):
        await asyncio.gather(*(forward_event_to_streaming_hub(evt) for evt in events))
"""

import os
from typing import Dict
from utils.logger import get_logger
from infrastructure.kafka.producer_singleton import kafka_producer

logger = get_logger("forwarder_mcpserver")


async def forward_event_to_streaming_hub(
    event: Dict,
) -> bool:
    """
    Async forward an event to go fiber streaming hub via kafka

    Args:
        event (Dict): The event payload to send (must match with Go model.Event)

    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    try:
        await kafka_producer.produce("ingest_topic", event)
        return True
    except Exception as e:
        logger.error(f"failed to forward event to kafka: {e}")
        return False
