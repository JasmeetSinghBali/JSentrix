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

		// Register client conn with redisbroadcaster
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

		// Add ping/pong handlers for connection health heartbeat mech and help detection of dead conn faster
		conn.SetPingHandler(func(message string) error {
			log.Printf("Recieved ping from %s", clientID)
			return conn.WriteControl(websocket.PongMessage, []byte(message), time.Now().Add(time.Second))
		})
		conn.SetPongHandler(func(message string) error {
			log.Printf("Recieved pong from %s", clientID)
			return nil
		})
		// Main message handling loop
		for {
			msgType, msg, err := conn.ReadMessage()
			if err != nil {
				if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway) {
					log.Printf("Unexpected close for %s: %v", clientID, err)
				}
				break
			}

			// Handle incoming messages i.e messages sent from the websocket client to the server for example if electron client sends a message
			switch msgType {
			case websocket.TextMessage:
				log.Printf("Recieved msg from %s: %s", clientID, string(msg))
				// 🎈 custom message processing logic can go here
			}
		}
	}
}
