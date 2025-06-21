// streaming-hub/internal/delivery/delivery.go
package delivery

import (
	_ "github.com/JasmeetSinghBali/JSentrix/streaming-hub/docs"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/config"
	httpdelivery "github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/delivery/http"
	wsdelivery "github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/delivery/ws"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/service"
	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/swagger"
)

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

	// HTTP routes
	app.Get("/health", httpdelivery.HealthCheck)
	app.Post("/login", httpdelivery.LoginHandler)
	// Serve Swagger UI at /swagger/index.html
	app.Get("/swagger/*", swagger.HandlerDefault)

	// WebSocket routes
	app.Use("/ws", func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			c.Locals("allowed", true)
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	})
	app.Use("/ws", wsdelivery.WebSocketAuthMiddleware) // Auth middleware
	app.Get("/ws", websocket.New(wsdelivery.WebSocketHandler(broadcaster)))

	// Example of using config in a route
	// app.Get("/config", func(c *fiber.Ctx) error {
	// 	return c.JSON(fiber.Map{
	// 		"redis_addr": cfg.RedisAddr,
	// 		"kafka_brokers": cfg.KafkaBrokers,
	// 	})
	// })

	return app
}
