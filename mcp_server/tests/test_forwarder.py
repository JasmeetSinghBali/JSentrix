import asyncio
import pytest
from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub


@pytest.mark.asyncio
async def test_forward_event_to_real_streaming_hub():
    event = {
        "event": "log",
        "message": "Integration test event",
        "stream_id": "test-stream-123",
    }

    # Call the real streaming hub service (make sure it's running)
    success = await forward_event_to_streaming_hub(event)

    assert success, "Failed to forward event to real streaming hub"
