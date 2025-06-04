> start the fastapi-gateway and mcp_server.py as subprocess stdio mode
```bash
uv run ./main.py

# lifecycle:

- When the gateway shuts down, it sends a termination signal to the MCP server subprocess.

- The MCP server catches this signal, runs cleanup code (e.g., closes DB, flushes logs), and exits gracefully.

- The gateway allows up to 5 seconds for the MCP server to finish cleanup before force-killing it.

# polished gateway
gateway/
├── main.py               # App entrypoint
├── config.py             # Config & env vars
├── database.py           # DB connection & setup
├── models.py             # SQLAlchemy & Pydantic models
├── schemas.py            # Pydantic request/response models
├── auth.py               # Auth utils, JWT, RBAC
├── dependencies.py       # Custom FastAPI dependencies
├── api/
│   ├── __init__.py
│   ├── routes_auth.py    # /token, /onboard
│   └── routes_tools.py   # /listtools, /tools/{tool_name}/invoke
├── utils/
│   ├── __init__.py
│   └── security.py       # Password hashing, etc.
├── .env                  # Secrets (excluded from git)
└── README.md



```