"""
mcp_server/interface/mcp_server.py

Entry point for the MCP server (FastMCP).
- Registers tools and shutdown logic.
- Starts the server (defaults to stdio when run as subprocess, or HTTP API with --http).

Usage:
    python -m interface.mcp_server          # stdio (subprocess mode)
    python -m interface.mcp_server --http   # HTTP and JSONRPC supp API mode (for Docker/microservices) without tracers log pesistance only console tracers
    python -m interface.mcp_server --http > tracers/logs/mcp_server_trace.log 2>&1 # http api and jsonrpc supp mode with tracers log persistance inside tracers/logs/mcp_server_trace.log and no console tracers
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

# tool modules
from tools.basic_tools import ping, add
from tools.streaming_tools import streaminges, abortinges

# qdrant
from infrastructure.qdrant_setup import safe_create_memory_collection

# 🚀 Ensure Qdrant collection memory_events exists
safe_create_memory_collection()

# --- MCP setup ---
logger = get_logger("jsentrix")
mcp = FastMCP("TransactionMonitorMCP")


# Register tools
mcp.tool()(ping)
mcp.tool()(add)
mcp.tool("streaminges")(streaminges)
mcp.tool("abortinges")(abortinges)

# --- Cleanup  ---
_cleanup_lock = threading.Lock()
_cleanup_called = False


def _any_async_shutdown_callbacks():
    from utils.lifecycle import _shutdown_callbacks

    return any(inspect.iscoroutinefunction(cb) for cb in _shutdown_callbacks)


def cleanup(source="unknown"):
    """
    Runs all registered shutdown callbacks.
    If any callback is async, runs async_shutdown_all in a new event loop.
    Otherwise, runs shutdown_all (sync).
    """
    global _cleanup_called
    with _cleanup_lock:
        if not _cleanup_called:
            logger.info(
                f"MCP server: Running server cleanup before shutting down (triggered by {source})..."
            )
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


atexit.register(lambda: cleanup("atexit"))
signal.signal(signal.SIGTERM, lambda signum, frame: (cleanup("SIGTERM"), sys.exit(0)))
signal.signal(signal.SIGINT, lambda signum, frame: (cleanup("SIGINT"), sys.exit(0)))

# --- HTTP API (FastAPI) act as wrapper around fastmcp server tools as http rest endpoints ---
from contextlib import asynccontextmanager
from fastapi import Request, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from tracers.tracing import setup_tracing
from pydantic import BaseModel
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optionally, place any startup code here
    yield
    # Shutdown async_shutdown_all already handles both sync and async callbacks
    await async_shutdown_all()


app = FastAPI(title="MCP Server API", lifespan=lifespan)
tracer = setup_tracing(app)


class ToolInvokeRequest(BaseModel):
    arguments: dict = {}


def call_tool(tool_func, arguments):
    sig = inspect.signature(tool_func)
    param_names = list(sig.parameters.keys())
    param_len = len(param_names)

    # Prepare dummy stream if needed
    class DummyStream:
        async def send(self, msg):
            pass

    # Prepare the positional arguments list
    args_list = []

    # Case 1: streaminges/abortinges (with optional stream/context)
    if param_len >= 1 and param_names[0] == "args":
        args_list.append(arguments)
        # If 'stream' is in signature, append dummy or None
        if param_len >= 2 and param_names[1] == "stream":
            args_list.append(DummyStream())
        # If 'context' is in signature, append None
        if param_len >= 3 and param_names[2] == "context":
            args_list.append(None)
        # If 'registry' is in signature, append None
        if param_len >= 4 and param_names[3] == "registry":
            args_list.append(None)
        return tool_func(*args_list)
    else:
        # Case 2: add/ping and other classic tools
        filtered_args = {k: v for k, v in arguments.items() if k in param_names}
        return tool_func(**filtered_args)


# --- Utility for extracting tool fn for seemless tool invocation by tool_name and req.arguments ----
async def invoke_registered_tools(tool_manager, tool_name: str, arguments: dict):
    """
    Looks up and invokes a registered tool by name using the tool manager.
    Handles both sync and async tool functions.
    Raises HTTPException(404) if the tool is not found.
    """
    logger.debug(dir(tool_manager))
    logger.debug(tool_manager.__dict__)
    logger.info("🔨 ----mcp tool manager structure above---")

    tool_obj = tool_manager._tools[tool_name]
    if not tool_obj:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    # the actual callable tool Python func
    tool_func = tool_obj.fn
    try:
        result = call_tool(tool_func, arguments)
        if inspect.iscoroutine(result):
            result = await result
        return result
    except Exception as e:
        logger.error(f"Unknown error invoking tool : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Tool invocation failed: {e}")


# --- Fast API mcp wrapper routes ---
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/list_tools")
async def list_tools():
    """
    List all registered tools.
    """
    tools = await mcp.list_tools()
    logger.info(f"mcp tools logged: {str(tools)} sending them to source now...")
    return {"tools": tools}


@app.post("/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, req: ToolInvokeRequest):
    """
    Invoke a registered tool by name.
    """
    try:
        result = await invoke_registered_tools(
            mcp._tool_manager, tool_name, req.arguments
        )
        return {"result": result}
    except HTTPException as e:
        logger.error(f"Tool invocation failed: {e.detail}")
        # 📌 reraise so that fastapi can convert it into error response with the error automatically instead of 200 success
        raise


@app.post("/jsonrpc")
async def jsonrpc_endpoint(request: Request):
    req = await request.json()
    # Basic JSON-RPC 2.0 validation
    if (
        not isinstance(req, dict)
        or req.get("jsonrpc") != "2.0"
        or "method" not in req
        or "id" not in req
    ):
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": req.get("id") if isinstance(req, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request"},
            },
        )
    method = req["method"]
    params = req.get("params", {})
    rpc_id = req["id"]

    # Dispatch to registered tools (sync or async)
    try:
        tool_obj = mcp._tool_manager._tools.get(method)
        if not tool_obj:
            raise Exception("Method not found")
        tool_func = tool_obj.fn
        result = call_tool(tool_func, params)
        if inspect.iscoroutine(result):
            result = await result
        return {"jsonrpc": "2.0", "result": result, "id": rpc_id}
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": -32601 if "Method not found" in str(e) else -32603,
                "message": str(e),
            },
        }


# --- mcp_server Entrypoint ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP Server (FastMCP)")
    parser.add_argument(
        "--http", action="store_true", help="Run as HTTP server (FastAPI)"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="HTTP host")
    parser.add_argument("--port", type=int, default=9001, help="HTTP port")
    args = parser.parse_args()

    if args.http:
        logger.info("Starting MCP server (FastMCP HTTP API)...")
        uvicorn.run(app, host=args.host, port=args.port)
        logger.info("MCP server (HTTP) has stopped.")
    else:
        logger.info("Starting MCP server (FastMCP stdio mode)...")
        mcp.run()  # Defaults to stdio when run as subprocess
        logger.info("MCP server (stdio) has stopped.")
