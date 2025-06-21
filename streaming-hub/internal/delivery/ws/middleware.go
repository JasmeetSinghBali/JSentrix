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
	if clientID == "" || token == "" {
		return fiber.ErrUnauthorized
	}
	if !auth.ValidateSession(clientID, token) {
		return fiber.ErrUnauthorized
	}
	// Pass client_id to ws handler as fiber context locals as "client_id"
	c.Locals("client_id", clientID)
	return c.Next()
}
