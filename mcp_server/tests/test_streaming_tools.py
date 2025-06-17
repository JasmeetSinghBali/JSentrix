import pytest
import uuid
from tools.streaming_tools import streaminges, abortinges, active_streams


class DummyStream:
    def __init__(self):
        self.events = []

    async def send(self, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_streaminges_valid_stream_id():
    stream_id = str(uuid.uuid4())
    dummy_stream = DummyStream()
    args = {"stream_id": stream_id}
    result = await streaminges(args, dummy_stream)
    assert result["done"] is True
    assert result["stream_id"] == stream_id
    assert any("processing" in e["message"] for e in dummy_stream.events)


@pytest.mark.asyncio
async def test_streaminges_invalid_stream_id():
    dummy_stream = DummyStream()
    args = {"stream_id": "not-a-uuid"}
    result = await streaminges(args, dummy_stream)
    assert "error" in result
    assert "Invalid or missing stream_id" in result["error"]


@pytest.mark.asyncio
async def test_abortinges():
    stream_id = str(uuid.uuid4())
    # Simulate a running stream
    active_streams[stream_id] = True
    dummy_stream = DummyStream()
    args = {"stream_id": stream_id}
    context = {}
    result = await abortinges(args, dummy_stream, context)
    assert result["aborted"] is True
    assert result["stream_id"] == stream_id
    assert active_streams[stream_id] is False


@pytest.mark.asyncio
async def test_abortinges_nonexistent():
    stream_id = str(uuid.uuid4())
    dummy_stream = DummyStream()
    args = {"stream_id": stream_id}
    context = {}
    result = await abortinges(args, dummy_stream, context)
    assert "error" in result
    assert result["error"] == "No such stream"
