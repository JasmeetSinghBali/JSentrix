"""
mcp_server/tools/basic_tools.py
"""

def ping() -> str:
    """Health check endpoint."""
    return "pong"

def add(a: int, b: int) -> int:
    """Add two number simple tool"""
    return a + b
