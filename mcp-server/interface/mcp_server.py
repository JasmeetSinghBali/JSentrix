"""
interface/mcp_server.py

Entry point for the MCP server (FastMCP).
- Registers tools and shutdown logic.
- Starts the server (defaults to stdio when run as subprocess).

Usage:
    python -m interface.mcp_server
"""

import sys
import os
import signal
import atexit
import threading
import asyncio
import inspect

# the project root set via sys.path as this runs as subprocess by gateway without this python assumes interface as the parent dir and cannot find utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP
from utils.logger import get_logger
from utils.lifecycle import shutdown_all, async_shutdown_all

logger = get_logger("jsentrix")
mcp = FastMCP("TransactionMonitorMCP")


@mcp.tool()
def ping() -> str:
    """Health check endpoint."""
    return "pong"


@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b


_cleanup_lock = threading.Lock()
_cleanup_called = False


def _any_async_shutdown_callbacks():
    # Check if any registered callback is async
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
            # Detect if any async callbacks are registered
            if _any_async_shutdown_callbacks():
                logger.info(
                    "MCP server: Detected async shutdown callbacks, running async shutdown."
                )
                try:
                    asyncio.run(async_shutdown_all())
                except RuntimeError as e:
                    # If already in an event loop (rare in CLI), fallback to create task
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


atexit.register(
    cleanup
)  # ensures cleanup is called when sys.exit() is called or script completes
# 📌 external signal interuptions signal handlers for diff cases
signal.signal(signal.SIGTERM, signal_handler)  # kill or system shutdown
signal.signal(signal.SIGINT, signal_handler)  # force console based


if __name__ == "__main__":
    logger.info("Starting MCP server (FastMCP)...")
    mcp.run()  # Defaults to stdio when run as subprocess
    logger.info("MCP server has stopped.")
