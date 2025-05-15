from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TransactionMonitorMCP")

@mcp.tool()
def ping() -> str:
    return "pong"

@mcp.tool()
def add(a: int, b: int) -> int:
    return a + b

if __name__ == "__main__":
    mcp.run()  # Defaults to stdio when run as subprocess
