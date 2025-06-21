// streaming-hub/internal/delivery/ws/handler.go
package ws

import (
	"log"
	"time"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/auth"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/service"
	"github.com/gofiber/contrib/websocket"
)

const InvalidTokenCloseCode = 4001

// WebSocketHandler handles websocket connections
func WebSocketHandler(broadcaster *service.RedisBroadcaster) func(*websocket.Conn) {
	return func(conn *websocket.Conn) {
		// Extract clientID from context set by ws/middleware.go
		clientID, ok := conn.Locals("client_id").(string)
		if !ok {
			log.Println("client_id not found in context")
			conn.Close()
			return
		}

		// Check TTL
		ttl, err := auth.GetTTL(clientID)
		if err != nil || ttl <= 0 {
			log.Printf("Session expired or not found for client_id=%s", clientID)
			conn.WriteControl(
				websocket.CloseMessage,
				websocket.FormatCloseMessage(InvalidTokenCloseCode, "Session expired"),
				time.Now().Add(time.Second),
			)
			conn.Close()
			return
		}
		// Optionally, if TTL is less than a threshold (e.g. 10 seconds), proactively close
		if ttl < 10*time.Second {
			log.Printf("Session TTL too low for client_id=%s: %v", clientID, ttl)
			conn.WriteControl(
				websocket.CloseMessage,
				websocket.FormatCloseMessage(InvalidTokenCloseCode, "Session about to expire"),
				time.Now().Add(time.Second),
			)
			conn.Close()
			return
		}

		broadcaster.Register(conn)
		defer func() {
			broadcaster.Unregister(conn)
			// delete the session on disconnect
			if err := auth.DeleteSession(clientID); err != nil {
				log.Printf("Failed to delete session for %s: %v", clientID, err)
			} else {
				log.Printf("Session deleted for %s", clientID)
			}
		}()

		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				break
			}
		}
	}
}
