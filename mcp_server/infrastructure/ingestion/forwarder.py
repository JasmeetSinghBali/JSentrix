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
from typing import Dict, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()


def get_streaming_hub_url() -> str:
    """
    Loads and caches the Streaming Hub service URL from environment variables
    Raises an error if not set
    """
    url = os.getenv("STREAMING_HUB_SERVICE", None)
    if not url:
        raise EnvironmentError("STREAMING_HUB_SERVICE env variable is not set")
    return url


async def forward_event_to_streaming_hub(
    event: Dict,
    url: Optional[str] = None,
    retries: int = 3,
    timeout: int = 3,
    backoff: float = 1.0,
    logger: Optional[object] = None,
) -> bool:
    """
    Async forward an event to go fiber streaming hub /ingest endpoint

    Args:
        event (Dict): The event payload to send (must match with Go model.Event)
        url (str,Optional): The url of the /ingest endpoint defaults to env var
        retries (int): Number of retry attempts on failure
        timeout (int): Timeout for the HTTP request in seconds
        backoff (float): Seconds to wait between retries
        logger (object, optional): Logger instance with .info/.error methods

    Returns:
        bool: True if the event was sent successfully, False otherwise
    """
    if url is None:
        url = get_streaming_hub_url()
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                resp = await client.post(
                    url, json=event, headers={"Content-Type": "application/json"}
                )
                if resp.status_code == 202:
                    if logger:
                        logger.info(f"Event forwarded: {event}")
                    return True
                else:
                    msg = f"Unexpected status {resp.status_code}:{resp.text}"

                    if logger:
                        logger.error(msg)
                    else:
                        print(msg)
            except Exception as e:
                msg = f"Attempt {attempt}: Error sending event: {e}"
                if logger:
                    logger.error(msg)
                else:
                    print(msg)
            if attempt < retries:
                await asyncio.sleep(backoff)
    return False
