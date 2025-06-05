> start the fastapi-gateway and mcp_server.py as subprocess stdio mode
```bash
uv run ./main.py

# lifecycle:

- When the gateway shuts down, it sends a termination signal to the MCP server subprocess.

- The MCP server catches this signal, runs cleanup code (e.g., closes DB, flushes logs), and exits gracefully.

- The gateway allows up to 5 seconds for the MCP server to finish cleanup before force-killing it.

# polished gateway
gateway/
├── src/
│   ├── core/                  # Domain layer (pure Python)
│   │   ├── config/            # Configuration models
│   │   │   └── settings.py
│   │   └── models/            # Pydantic models
│   │       └── user.py
│   │
│   ├── infrastructure/        # External implementations
│   │   ├── database/          # DB connections
│   │   │   ├── session.py
│   │   │   └── models.py      # SQLAlchemy models
│   │   ├── auth/              # Auth implementations
│   │   │   ├── jwt.py
│   │   │   └── security.py
│   │
│   ├── application/           # Use cases & services
│   │   ├── use_cases/
│   │   │   ├── auth.py
│   │   └── services/          # Internal services
│   │       └── logger.py
│   │
│   ├── api/                   # Presentation layer
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   └── tools.py
|   |   |   └── dashboard.py
│   │
│   └── main.py                # App initialization
│
├── tests/                     # Test suite
├── .env                       # Environment variables
├── pyproject.toml


```