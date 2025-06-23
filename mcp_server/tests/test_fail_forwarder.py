"""
mcp_server/tests/test_fail_fowarder.py

This produces to ingest_topic_dlq, which causes Kafka to auto-create this topic
— and the next time the DLQ consumer starts, it will find it.

Success:
    shud appear in mcp_server logs
    ✅ Successfully resent event to topic ingest_topic
"""

import pytest
from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub


@pytest.mark.asyncio
async def test_fail_forward_event_to_kafka():
    class Bad:
        pass  # Not JSON serializable

    # Break Kafka send, but allow DLQ serialization to succeed
    event = {
        "event": "log",
        "message": "fail me",
        "stream_id": "deadbeef",
        "data": {"bad_field": Bad()},  # will break forward_event_to_kafka
    }

    success = await forward_event_to_streaming_hub(event)
    assert not success  # Now expect it to fail!
