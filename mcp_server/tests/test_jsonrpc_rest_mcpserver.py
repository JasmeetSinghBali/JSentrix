import pytest
import httpx

MCP_SERVER_URL = "http://localhost:9001"


@pytest.mark.asyncio
async def test_rest_add_endpoint():
    """
    Test the legacy REST endpoint for tool invocation.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{MCP_SERVER_URL}/tools/add/invoke",
            json={"arguments": {"a": 2, "b": 3}},
            timeout=5,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert data["result"] == 5


@pytest.mark.asyncio
async def test_jsonrpc_add_method():
    """
    Test the new JSON-RPC 2.0 endpoint for tool invocation.
    """
    async with httpx.AsyncClient() as client:
        req = {
            "jsonrpc": "2.0",
            "method": "add",
            "params": {"a": 2, "b": 3},
            "id": 42,
        }
        resp = await client.post(
            f"{MCP_SERVER_URL}/jsonrpc",
            json=req,
            timeout=5,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 42
        assert "result" in data
        assert data["result"] == 5


@pytest.mark.asyncio
async def test_jsonrpc_method_not_found():
    """
    Test JSON-RPC error for unknown method.
    """
    async with httpx.AsyncClient() as client:
        req = {
            "jsonrpc": "2.0",
            "method": "nonexistent_method",
            "params": {},
            "id": 99,
        }
        resp = await client.post(
            f"{MCP_SERVER_URL}/jsonrpc",
            json=req,
            timeout=5,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 99
        assert "error" in data
        assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_jsonrpc_invalid_request():
    """
    Test JSON-RPC error for invalid request format.
    """
    async with httpx.AsyncClient() as client:
        # Missing 'jsonrpc' and 'id'
        req = {
            "method": "add",
            "params": {"a": 2, "b": 3},
        }
        resp = await client.post(
            f"{MCP_SERVER_URL}/jsonrpc",
            json=req,
            timeout=5,
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["jsonrpc"] == "2.0"
        assert data["error"]["code"] == -32600
