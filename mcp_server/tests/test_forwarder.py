"""
Integration test: Forwards multiple mock events to Kafka for the running streaming hub

Requirements:
    docker-compose up -d redis kafka streaming-hub traefik
    # Ensure both jsentrix-streaming-hub-1 and jsentrix-streaming-hub-2 are healthy and connected to Kafka.
    # Electron app (or test WebSocket client) should be connected to /ws to verify event broadcast.

How it works:
    - Each call to forward_event_to_streaming_hub(event) produces an event to the Kafka topic (e.g. "ingest_topic").
    - The Go streaming-hub consumes from Kafka and broadcasts events to all connected WebSocket clients.
    - To verify end-to-end, connect a WebSocket client to /ws and assert events are received.
Run:
    pytest ./tests/test_forwarder.py

Note:
    This test only verifies that events are successfully produced to Kafka.
    For full E2E, run a WebSocket client and assert receipt of these events or run electorn client and see events log in ui
"""

import pytest
from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub


@pytest.mark.asyncio
async def test_forward_event_to_kafka_multiple():
    for i in range(10):
        event = {
            "event": "log",
            "message": f"Integration test event {i}",
            "stream_id": f"test-stream-{i}",
        }
        success = await forward_event_to_streaming_hub(event)
        assert success, f"Failed to forward event {i} to Kafka"
