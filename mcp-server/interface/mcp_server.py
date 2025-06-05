"""
mcp-server/interface/mcp_server.py

Entry point for the MCP server (FastMCP).
- Registers tools and shutdown logic.
- Starts the server (defaults to stdio when run as subprocess, or HTTP API with --http).

Usage:
    python -m interface.mcp_server          # stdio (subprocess mode)
    python -m interface.mcp_server --http   # HTTP API mode (for Docker/microservices)
"""

import sys
import os
import signal
import atexit
import threading
import asyncio
import inspect

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP
from utils.logger import get_logger
from utils.lifecycle import shutdown_all, async_shutdown_all

# --- MCP setup ---
logger = get_logger("jsentrix")
mcp = FastMCP("TransactionMonitorMCP")


@mcp.tool()
def ping() -> str:
    """Health check endpoint."""
    return "pong"


@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b


# --- Cleanup  ---
_cleanup_lock = threading.Lock()
_cleanup_called = False


def _any_async_shutdown_callbacks():
    from utils.lifecycle import _shutdown_callbacks

    return any(inspect.iscoroutinefunction(cb) for cb in _shutdown_callbacks)


def cleanup():
    """
    Runs all registered shutdown callbacks.
    If any callback is async, runs async_shutdown_all in a new event loop.
    Otherwise, runs shutdown_all (sync).
    """
    global _cleanup_called
    with _cleanup_lock:
        if not _cleanup_called:
            logger.info("MCP server: Running server cleanup before shutting down...")
            if _any_async_shutdown_callbacks():
                logger.info(
                    "MCP server: Detected async shutdown callbacks, running async shutdown."
                )
                try:
                    asyncio.run(async_shutdown_all())
                except RuntimeError as e:
                    logger.error(f"Error running async shutdown: {e}")
                    loop = asyncio.get_event_loop()
                    loop.create_task(async_shutdown_all())
            else:
                shutdown_all()
            _cleanup_called = True
        else:
            logger.info("MCP server: Cleanup already performed")


def signal_handler(signum, frame):
    logger.info(f"MCP server: Recieved signal {signum}, shutting down")
    cleanup()
    sys.exit(0)


atexit.register(cleanup)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# --- HTTP API (FastAPI) ---
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="MCP Server API")


class ToolInvokeRequest(BaseModel):
    arguments: dict = {}


@app.get("/list_tools")
async def list_tools():
    """
    List all registered tools.
    """
    # print(dir(mcp))
    tools = await mcp.list_tools()
    print(tools)
    return {"tools": tools}


@app.post("/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, req: ToolInvokeRequest):
    """
    Invoke a registered tool by name.
    """
    tool = mcp.tools_map.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    try:
        result = tool(**req.arguments)
        if inspect.iscoroutine(result):
            result = await result
        return {"result": result}
    except Exception as e:
        logger.error(f"Tool invocation failed: {e}")
        raise HTTPException(status_code=500, detail="Tool invocation failed")


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Entrypoint ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server (FastMCP)")
    parser.add_argument(
        "--http", action="store_true", help="Run as HTTP server (FastAPI)"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=9000, help="HTTP port")
    args = parser.parse_args()

    if args.http:
        logger.info("Starting MCP server (FastMCP HTTP API)...")
        uvicorn.run(app, host=args.host, port=args.port)
        logger.info("MCP server (HTTP) has stopped.")
    else:
        logger.info("Starting MCP server (FastMCP stdio mode)...")
        mcp.run()  # Defaults to stdio when run as subprocess
        logger.info("MCP server (stdio) has stopped.")
