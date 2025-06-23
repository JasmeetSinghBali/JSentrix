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
import asyncio
import json
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
        if isinstance(event, str):
            event = json.loads(event)
        # wait_for to avoid streaming pipeline getting hijacked by some broker/netowrk/infinite retry loops
        await asyncio.wait_for(kafka_producer.produce("ingest_topic", event), timeout=5)
        return True
    except Exception as e:
        logger.error(f"failed to forward event to kafka: {e}")
        # 📌 Serialize safely before pushing to DLQ
        clean_event = make_serializable(event)
        await produce_to_dlq(clean_event, reason=str(e))
        return False


def make_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    else:
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            return str(obj)


async def produce_to_dlq(event: dict, reason: str = "Unknown error"):
    """
    Push failed events to DLQ topic with retry metadata
    """
    try:
        clean_event = make_serializable(event)
        dlq_event = {
            "original_event": clean_event,
            "reason": reason,
            "retry_attempts": 0,
            "span_id": event.get("data", {}).get("context", {}).get("span_id"),
            "trace_id": event.get("data", {}).get("context", {}).get("trace_id"),
        }
        await kafka_producer.produce("ingest_topic_dlq", dlq_event)
        logger.warning(
            f"🚨 Event sent to DLQ due to: {reason}\nPayload: {json.dumps(dlq_event, indent=2)}"
        )
    except Exception as e:
        logger.critical(f"failed to write to DLQ: {e}")
