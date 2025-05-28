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

# the project root set via sys.path as this runs as subprocess by gateway without this python assumes interface as the parent dir and cannot find utils 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP
from utils.logger import get_logger
from utils.lifecycle import shutdown_all

logger=get_logger("jsentrix")

mcp = FastMCP("TransactionMonitorMCP")

@mcp.tool()
def ping() -> str:
    """Health check endpoint."""
    return "pong"

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

# 🎈 need to find alternative in FastMCP for lifespan management like fastAPI
# @mcp.on_event("shutdown")
# def on_shutdown():
#     """Handles graceful shutdown of the MCP server."""
#     logger.info("Shutting down MCP server...")
#     shutdown_all()

if __name__ == "__main__":
    logger.info("Starting MCP server (FastMCP)...")
    mcp.run()  # Defaults to stdio when run as subprocess
    logger.info("MCP server has stopped.")