// streaming-hub/internal/delivery/http/handler.go
// Package http contains Fiber handlers for HTTP and Websocket endpoints
package http

import (
	"log"
	"os"

	_ "github.com/JasmeetSinghBali/JSentrix/streaming-hub/docs"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/config"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/model"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/service"
	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/swagger"
)

// HealthCheck godoc
// @Summary      Health check
// @Description  Returns 200 if service is up
// @Tags         health
// @Success      200  {string}  string  "ok"
// @Router       /health [get]
func HealthCheck(c *fiber.Ctx) error {
	return c.SendStatus(fiber.StatusOK)
}

// IngestEvent godoc
// @Summary      Ingest event for broadcast
// @Description  Ingests an event to be broadcast to all clients
// @Tags         ingest
// @Accept       json
// @Produce      json
// @Param        event  body      model.Event  true  "Event payload"
// @Success      202    {string}  string       "accepted"
// @Failure      400    {string}  string       "invalid event"
// @Router       /ingest [post]
func IngestEvent(broadcaster *service.RedisBroadcaster) fiber.Handler {
	return func(c *fiber.Ctx) error {
		var evt model.Event
		if err := c.BodyParser(&evt); err != nil {
			log.Println("Failed to parse event:", err)
			return c.Status(fiber.StatusBadRequest).SendString("Invalid event")
		}
		msg := c.Body()
		// Log the event and the container hostname for replica identification
		hostname, _ := os.Hostname()
		log.Printf("[Replica: %s] EVENT %d: %+v\n", hostname, evt.StreamID, evt)
		os.Stdout.Sync()
		broadcaster.Broadcast(msg)
		return c.SendStatus(fiber.StatusAccepted)
	}
}

// WebSocketHandler handles websocket connections
func WebSocketHandler(broadcaster *service.RedisBroadcaster) fiber.Handler {
	return websocket.New(func(conn *websocket.Conn) {
		broadcaster.Register(conn)
		defer broadcaster.Unregister(conn)
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				break
			}
		}
	})
}

// WebSocketEndpoint godoc
// @Summary      WebSocket endpoint for real-time streaming
// @Description  Upgrade to WebSocket at ws://localhost:4001/ws using a WebSocket client (not Swagger UI).
// @Tags         websocket
// @Produce      plain
// @Success      101 {string} string "Switching Protocols"
// @Router       /ws [get]
func WebSocketEndpointDoc(c *fiber.Ctx) error {
	return c.SendStatus(fiber.StatusSwitchingProtocols)
}

// NewFiberApp initializes the Fiber app with all routes and handlers
func NewFiberApp(cfg *config.Config, broadcaster *service.RedisBroadcaster) *fiber.App {
	app := fiber.New()

	app.Get("/health", HealthCheck)

	app.Use("/ws", func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			c.Locals("allowed", true)
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	})
	app.Get("/ws", WebSocketHandler(broadcaster))

	// Note - the mcpserver<>streaming_hub are no decoupled by kafka ingest_event topic producer consumer pattern
	// Deprecated: app.Post("/ingest", IngestEvent(broadcaster))

	// Serve Swagger UI at /swagger/index.html
	app.Get("/swagger/*", swagger.HandlerDefault)

	// Example of using config in a route
	// app.Get("/config", func(c *fiber.Ctx) error {
	// 	return c.JSON(fiber.Map{
	// 		"redis_addr": cfg.RedisAddr,
	// 		"kafka_brokers": cfg.KafkaBrokers,
	// 	})
	// })

	return app
}
