// streaming-hub/internal/delivery/http/handler.go
// Package http contains Fiber handlers for HTTP and Websocket endpoints
package http

import (
	"log"
	"os"
	"time"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/auth"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/model"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/service"
	"github.com/gofiber/fiber/v2"
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

// deprecated: IngestEvent godoc
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

// Note - the mcpserver<>streaming_hub are no decoupled by kafka ingest_event topic producer consumer pattern
// Deprecated: app.Post("/ingest", IngestEvent(broadcaster))

// LoginHandler returns token and clientID
func LoginHandler(c *fiber.Ctx) error {
	clientId, token, err := auth.NewSession(24 * time.Hour)
	if err != nil {
		log.Printf("Error creating sesssion: %v", err)
		return fiber.ErrInternalServerError
	}
	return c.JSON(fiber.Map{
		"client_id":  clientId,
		"token":      token,
		"expires_in": 86400,
	})
}
