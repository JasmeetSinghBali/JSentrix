> start the fastapi-gateway and mcp_server.py as subprocess stdio mode
```bash
uv run ./main.py

# lifecycle:

- When the gateway shuts down, it sends a termination signal to the MCP server subprocess.

- The MCP server catches this signal, runs cleanup code (e.g., closes DB, flushes logs), and exits gracefully.

- The gateway allows up to 5 seconds for the MCP server to finish cleanup before force-killing it.
```