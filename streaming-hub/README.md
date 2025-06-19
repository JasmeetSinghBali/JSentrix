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
│   │   └── redis_broadcaster.go      # Broadcasting logic
│   ├── model/
│   │   └── event.go            # Event/message types
│   └── config/
│       └── config.go           # Config loading (env, flags)
│   └── redis/
│       └── redis.go            # redis go client instance
├── docs/
│   └── swagger.yaml            # OpenAPI/Swagger spec
├── test/
│   └── handler_test.go         # Mock tests for handlers
├── go.mod
├── go.sum
└── .dockerignore
└── Dockerfile
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

## Run streaming hub 

```bash
# streaming-hub
go run .\cmd\server\main.go
```

## Testing

Run all unit tests:

```bash
go test ./test
```

## Swagger

```bash
go install github.com/swaggo/swag/cmd/swag@latest
go get -u github.com/gofiber/swagger

# streaming-hub
# NOTE- rerun init command to regenerate docs make sure to delete the old docs/ inside streaming-hub
swag init -g cmd/server/main.go
# for specific doc output folder
swag init -g cmd/server/main.go -o docs

# check swagger ui
http://localhost:4001/swagger/
```

## Traefik

```bash
# reff : https://doc.traefik.io/traefik/getting-started/install-traefik/#use-the-official-docker-image
# traffic flow loadbalanced(only for the case of streaming-hub no direct access)
Client → Traefik (port 80) → Round-Robin → streaming-hub instances
```

## Scale streaming-hub to arbitary number

```bash
docker compose up -d --scale streaming-hub=4

# to exec into running instance streaming-hub
docker exec -it jsentrix-streaming-hub-1 sh
curl -v http://localhost:4001/health
```