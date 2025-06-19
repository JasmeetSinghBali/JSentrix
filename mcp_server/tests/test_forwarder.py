"""
Integration test: Forwards multiple mock events to the running streaming hub.

Requirements:
    docker-compose up -d redis streaming-hub traefik
    # Ensure both jsentrix-streaming-hub-1 and jsentrix-streaming-hub-2 are healthy and accessible via Traefik at http://localhost/ingest

How it works:
    - Each POST to http://localhost/ingest is routed by Traefik/load balancer to one replica (not both).
    - Sending multiple requests increases the chance that both replicas process at least one request (round-robin or load-balanced).
    - Check the logs of both streaming-hub replicas to confirm receipt.

Run:
    pytest ./tests/test_forwarder.py

Note:
    To confirm both replicas are receiving events, check logs for both containers after running this test.
"""

import pytest
from infrastructure.ingestion.forwarder import forward_event_to_streaming_hub


@pytest.mark.asyncio
async def test_forward_event_to_real_streaming_hub_multiple():
    for i in range(10):
        event = {
            "event": "log",
            "message": f"Integration test event {i}",
            "stream_id": f"test-stream-{i}",
        }
        success = await forward_event_to_streaming_hub(event)
        assert success, f"Failed to forward event {i} to streaming hub"
