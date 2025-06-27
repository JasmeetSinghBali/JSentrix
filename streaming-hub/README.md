# Streaming Hub

A production-grade, clean-architecture Go Fiber microservice for real-time event/log streaming to Electron apps.
- [x] Scalability (multiple streaming-hub instances share Kafka load)

- [x] Reliability (failover via Kafka consumer group rebalancing)

- [x] Real-time fan-out to all clients via Redis Pub/Sub

## flow

1. Only one instance of streaming-hub (the one that Kafka assigns the partition(s) to) actually consumes each Kafka event.

2. That instance then publishes the event to a common Redis channel (using RedisBroadcaster).

3. All streaming-hub instances subscribe to that Redis channel, so every instance receives the event—regardless of which one originally consumed it from Kafka.

4. Each instance then broadcasts the event to its own connected /ws WebSocket clients, ensuring no client misses any event, no matter which backend instance it’s connected to.

```bash
Why This Pattern?
Kafka consumer group provides load balancing and failover for backend processing.

Redis Pub/Sub provides real-time, cross-instance fan-out for WebSocket clients, enabling horizontal scaling of streaming-hub service.

pattern ensures scalable real-time architectures where all frontend clients to get every event, even when your backend is distributed across multiple containers or servers
```

```bash
<DEPRECATED> (BROADCAST-TO-ALL)
Kafka Topic
    │
    │ (one streaming-hub instance consumes each event)
    ▼
Redis Channel (Pub/Sub)
    │
    │ (all streaming-hub instances subscribe)
    ▼
WebSocket Clients (on all instances)

<CURRENT> (BROADCAST-TO-STREAM)
Kafka Topic
    │
    │ (one streaming-hub instance consumes each event)
    ▼
Redis Channel (Pub/Sub)
    │
    │ (all streaming-hub instances subscribe)
    ▼
Only WebSocket Clients In event.StreamID group

```

```bash
streaming-hub/
├── cmd/
│   └── server/
│       └── main.go             # Entrypoint
├── internal/
│   ├── delivery/
│   │   ├── http/
│   │   │   └── handler.go      # HTTP handlers
│   │   ├── ws/
│   │   │   └── handler.go      # Websocket handlers
│   │   │   └── middleware.go   # websocket middleware
│   │   └── delivery.go         # NewFiberApp initializes the Fiber app with all http/ws routes & handlers
│   ├── service/
│   │   └── redis_broadcaster.go      # Broadcasting logic
|   |   └── kafka_consumer.go         # kafka ingest_event consumer from mcp_server
│   ├── model/
│   │   └── event.go            # Event/message types
│   └── config/
│       └── config.go           # Config loading (env, flags)
│   └── redis/
│       └── redis.go            # redis go client instance
│   └── auth/
│       └── session_store.go    # session_store clientstreamhubwstokens:abc123 = 7f8a9c1e2d...   (the token)
│   └── utils/
│       └── kafka.go    # ensures all kafka-topic exist before the kafka consumer register in diff stream-hub instances
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
- `POST /login` - Login returns token(ttl) and clientId
- `GET /ws` — WebSocket endpoint for clients
- Deprecated: `POST /ingest` — Ingest events (from MCP server) as MCP_SERVER and streaming_hub comm is now via kafka events with confluent-kafka and redisBroadcasting to the clients attached to streaming_hub instances/replicas

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

## Auto Load Balancing 

```bash
# bring down the container that is handling the consumption of events and broadcasting it 
docker stop jsentrix-streaming-hub-2
# now for furrther events the other jsentrix-streaming-hub-1 will have logs of events consumption from kafka and broadcasting

NOTE- though both the instances of streaming-hub will have access to same redis event so that no clients associated to their respective streaming-hub misses the event even though only 1 inst actually consumes the kafka topic

# to exec into running instance streaming-hub
docker exec -it jsentrix-streaming-hub-1 sh
curl -v http://localhost:4001/health
```

## RedisBroadcaster
```bash
Redis Pub/Sub is essential for broadcasting events to all clients across all streaming-hub instances.

It enables scalable, real-time delivery regardless of which instance consumed the Kafka message.

Without it, only a subset of your clients would get updates.
```


## Redis Keyspace With All Three Patterns
```bash
Key                                 Example	Type	Used by	            Purpose
clientstreamhubwstokens:abc123	     String	        streaming-hub	WebSocket session token for a client
active_streams	                      Set	        mcp_server	    Tracks active streaming session IDs
triageevents	                     PubSub	        streaming-hub	Channel name for real-time broadcasting
```