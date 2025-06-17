// Package service provides logic for broadcasting events to clients.
package service

import (
	"sync"

	"github.com/gofiber/contrib/websocket"
)

// Broadcaster manages a set of WebSocket clients and allows broadcasting messages to all of them
// It ensures safe concurrent access using a sync.Mutex to prevent race conditions during client management
//
//	{
//		0xc00010e000: true, // pointer to a websocket.Conn
//		0xc000114060: true,
//		0xc000120090: true,
//	}
type Broadcaster struct {
	clients map[*websocket.Conn]bool // Active WebSocket connections
	mutex   sync.Mutex               // Mutex to ensure thread-safe access to the clients map
}

func NewBroadcaster() *Broadcaster {
	return &Broadcaster{
		clients: make(map[*websocket.Conn]bool),
	}
}

// Register's/adds a new client connection to the *Broadcaster same instance struct
func (b *Broadcaster) Register(conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	b.clients[conn] = true
}

// Unregister's/remove existing client connection to the *Broadcaster same instance struct
func (b *Broadcaster) Unregister(conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	delete(b.clients, conn)
}

// Broadcast sends a message to all connected clients
func (b *Broadcaster) Broadcast(msg []byte) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	for conn := range b.clients {
		if err := conn.WriteMessage(websocket.TextMessage, msg); err != nil {
			conn.Close()
			delete(b.clients, conn)
		}
	}
}
