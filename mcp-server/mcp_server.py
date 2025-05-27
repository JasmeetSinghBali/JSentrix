from mcp.server.fastmcp import FastMCP
from utils.neo4j_utils import get_neo4j_driver
from utils.logger import get_logger
from utils.lifecycle import shutdown_all

logger=get_logger("jsentrix")

mcp = FastMCP("TransactionMonitorMCP")

@mcp.tool()
def ping() -> str:
    return "pong"

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

@mcp.on_event("shutdown")
def on_shutdown():
    logger.info("Shutting down MCP server...")
    shutdown_all()

if __name__ == "__main__":
    mcp.run()  # Defaults to stdio when run as subprocess
