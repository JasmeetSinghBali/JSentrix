"""
mcp_server/tests/test_qdrant_connection.py

Tests for Qdrant connection via both sync and async clients.

Requirements:
    - Qdrant server must be running and accessible at the configured host/port.
    - pytest
    - pytest-asyncio

Run with:
    From inside mcp_server, set PYTHONPATH:
        $env:PYTHONPATH="Drive:\dummy\JSentrix\mcp_server"
        pytest tests/test_qdrant_connection.py
"""

import pytest
from utils.qdrant_utils import get_qdrant_client, get_async_qdrant_client


def test_qdrant_connection():
    client = get_qdrant_client()
    collections = client.get_collections()
    # collections is a CollectionsResponse object
    assert hasattr(collections, "collections"), "No collections attribute in response"
    print("Qdrant collections (sync):", collections.collections)


@pytest.mark.asyncio
async def test_async_qdrant_connection():
    client = get_async_qdrant_client()
    collections = await client.get_collections()
    assert hasattr(
        collections, "collections"
    ), "No collections attribute in async response"
    print("Qdrant collections (async):", collections.collections)


if __name__ == "__main__":
    test_qdrant_connection()
