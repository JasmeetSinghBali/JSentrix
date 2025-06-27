// streaming-hub/internal/delivery/ws/middleware.go
package ws

import (
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/auth"
	"github.com/gofiber/fiber/v2"
)

// WebSocketAuthMiddleware checks client_id and token in query params
func WebSocketAuthMiddleware(c *fiber.Ctx) error {
	clientID := c.Query("client_id")
	token := c.Query("token")
	streamID := c.Query("stream_id")
	if clientID == "" || token == "" {
		return fiber.NewError(fiber.StatusUnauthorized, "Missing client_id or token")
	}
	if streamID == "" {
		return fiber.NewError(fiber.StatusBadRequest, "Missing stream_id")
	}
	if !auth.ValidateSession(clientID, token) {
		return fiber.NewError(fiber.StatusUnauthorized, "Invalid session")
	}
	// Inject context values for use in ws handler client_id and stream_id
	c.Locals("client_id", clientID)
	c.Locals("stream_id", streamID)
	return c.Next()
}
