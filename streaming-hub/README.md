# Streaming Hub

A production-grade, clean-architecture Go Fiber microservice for real-time event/log streaming to Electron apps.

```bash
streaming-hub/
├── cmd/
│   └── server/
│       └── main.go             # Entrypoint
├── internal/
│   ├── delivery/
│   │   ├── http/
│   │   │   └── handler.go      # HTTP & WebSocket handlers
│   ├── service/
│   │   └── broadcaster.go      # Broadcasting logic
│   ├── model/
│   │   └── event.go            # Event/message types
│   └── config/
│       └── config.go           # Config loading (env, flags)
├── docs/
│   └── swagger.yaml            # OpenAPI/Swagger spec
├── test/
│   └── handler_test.go         # Mock tests for handlers
├── go.mod
├── go.sum
└── README.md
└── .env
└── .example.env
```

## Endpoints

- `GET /health` — Health check
- `GET /ws` — WebSocket endpoint for clients
- `POST /ingest` — Ingest events (from MCP server)

## Architecture

- Clean separation of delivery, service, and model layers
- Concurrency-safe client management
- Easily extensible for Redis, JWT, metrics, etc.

## Testing

Run all unit tests:
