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
└── tracers/                    # tracers opentelemetry
|    ├── __init__.py
|
├── tests/                     # Test suite
├── .env                       # Environment variables
├── pyproject.toml

# to check dockerized postgres is up
docker exec postgresjsentrix pg_isready
# shud output accepting connections

# interactive shell with postgres docker container
docker exec -it postgresjsentrix psql -U postgres -d jsentrixdb
\dt
\l
\q

# openapi specification swagger docs at
http://localhost:8080/docs


```