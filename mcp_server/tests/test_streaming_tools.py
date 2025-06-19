"""
Test suite for streaminges and abortinges tools using Redis-backed active stream registry.

Requirements:
- Running Redis server (default: localhost:6379 or as set in .env)
- python-dotenv, redis[async], pytest, pytest-asyncio

To run:
    pytest tests/test_streaming_tools.py

If using Docker Compose, start Redis with:
    docker compose up -d redis

Ensure your .env is configured with REDIS_URL if not using the default.
"""

import uuid
import pytest
import pytest_asyncio
from tools.streaming_tools import streaminges, abortinges
from infrastructure.redis_stream_registry import AsyncStreamRegistry


class DummyStream:
    def __init__(self):
        self.events = []

    async def send(self, event):
        self.events.append(event)


@pytest_asyncio.fixture
async def registry():
    reg = AsyncStreamRegistry()
    await reg.connect()
    await reg._redis.delete(reg.active_streams_key)
    yield reg
    await reg._redis.delete(reg.active_streams_key)
    await reg.close()


@pytest.mark.asyncio
async def test_streaminges_valid_stream_id(registry):
    stream_id = str(uuid.uuid4())
    dummy_stream = DummyStream()
    args = {"stream_id": stream_id}
    result = await streaminges(args, dummy_stream, registry=registry)
    assert result["done"] is True
    assert result["stream_id"] == stream_id
    assert any("processing" in e["message"] for e in dummy_stream.events)
    assert not await registry.is_active(stream_id)


@pytest.mark.asyncio
async def test_streaminges_invalid_stream_id(registry):
    dummy_stream = DummyStream()
    args = {"stream_id": "not-a-uuid"}
    result = await streaminges(args, dummy_stream, registry=registry)
    assert "error" in result
    assert "Invalid or missing stream_id" in result["error"]


@pytest.mark.asyncio
async def test_abortinges(registry):
    stream_id = str(uuid.uuid4())
    dummy_stream = DummyStream()
    args = {"stream_id": stream_id}
    context = {}
    await registry.add(stream_id)
    result = await abortinges(args, dummy_stream, context, registry=registry)
    assert result["aborted"] is True
    assert result["stream_id"] == stream_id
    assert not await registry.is_active(stream_id)


@pytest.mark.asyncio
async def test_abortinges_nonexistent(registry):
    stream_id = str(uuid.uuid4())
    dummy_stream = DummyStream()
    args = {"stream_id": stream_id}
    context = {}
    result = await abortinges(args, dummy_stream, context, registry=registry)
    assert "error" in result
    assert result["error"] == "No such stream"
