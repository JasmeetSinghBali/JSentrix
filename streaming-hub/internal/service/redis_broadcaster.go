// streaming-hub/internal/service/redis_broadcaster.go
// Package service provides logic for broadcasting events to clients.
// manages websocketclient, broadcasting messages b/w clients using redis pub/sub pattern , ensuring thread safe oprn via goroutine via mutex
// now app can be scaled horizont multiple servers instances can share messages in real time via redis and broadcast them to their own connected clients
package service

import (
	"context"
	"log"
	"sync"

	myredis "github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/redis"
	"github.com/gofiber/contrib/websocket"
	"github.com/redis/go-redis/v9"
)

// Redis Broadcaster manages a set of WebSocket clients and uses Redis Pub/Sub for cross-instance broadcasting to them
// It ensures safe concurrent access using a sync.Mutex to prevent race conditions during client management
// clients map[*websocket.Conn]bool
//
//	{
//		0xc00010e000: true, // pointer to a websocket.Conn
//		0xc000114060: true,
//		0xc000120090: true,
//	}
type RedisBroadcaster struct {
	clients    map[*websocket.Conn]bool // Active WebSocket connections
	mutex      sync.Mutex               // Mutex to ensure thread-safe access to the clients map
	redis      *redis.Client            // go-redis third party client type
	channel    string                   // redis channel name to subscribe to /publish on
	ctx        context.Context          // manage goroutine cycle
	cancelFunc context.CancelFunc       // manage goroutine cycle
}

// NewRedisBroadcaster creates a new RedisBroadcaster and starts the subscriber goroutine
func NewRedisBroadcaster(channel string) *RedisBroadcaster {
	redisClient := myredis.GetClient()
	if redisClient == nil {
		log.Fatal("Redis client is nil! forgot to call Init!!")
	}
	ctx, cancel := context.WithCancel(context.Background())
	b := &RedisBroadcaster{
		clients:    make(map[*websocket.Conn]bool),
		redis:      redisClient, // always the singleton redis client
		channel:    channel,
		ctx:        ctx,
		cancelFunc: cancel,
	}
	go b.subscribe()
	return b
}

// Register's/adds a new websocket client connection to the *RedisBroadcaster same instance struct
func (b *RedisBroadcaster) Register(conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	b.clients[conn] = true
}

// Unregister's/remove existing websocket client connection to the *RedisBroadcaster same instance struct
func (b *RedisBroadcaster) Unregister(conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	delete(b.clients, conn)
}

// Broadcast/publishes the message to Redis channel, Other instance will also recieve this message via redis
func (b *RedisBroadcaster) Broadcast(msg []byte) {
	if err := b.redis.Publish(b.ctx, b.channel, msg).Err(); err != nil {
		log.Printf("Redis publish error: %v", err)
	}
}

// subscribe listens to the redis channel and forwards messages to all connected websocket clients
func (b *RedisBroadcaster) subscribe() {
	pubsub := b.redis.Subscribe(b.ctx, b.channel)
	defer pubsub.Close()

	ch := pubsub.Channel()

	for {
		select {
		case <-b.ctx.Done(): // waits for channel to close i.e ctx.Done() to shut down goroutines
			return
		case msg, ok := <-ch:
			if !ok { // ok will be false if the channel is closed
				return
			}
			b.dispatch([]byte(msg.Payload)) // dispatch msg from the channel to loca websocket clients
		}
	}
}

// dispatch sends the message to all connected WebSocket clients.
func (b *RedisBroadcaster) dispatch(msg []byte) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	for conn := range b.clients {
		if err := conn.WriteMessage(websocket.TextMessage, msg); err != nil {
			conn.Close()
			delete(b.clients, conn) // on failed conn that websocket client is removed
		}
	}
}

// Close stops the Redis subscription.
func (b *RedisBroadcaster) Close() {
	b.cancelFunc() // cancels/cleanup the background subscribe() goroutine
}
