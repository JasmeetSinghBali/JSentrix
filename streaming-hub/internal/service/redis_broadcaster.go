// streaming-hub/internal/service/redis_broadcaster.go
// Package service provides logic for broadcasting events to clients.
// manages websocketclient, broadcasting messages b/w clients using redis pub/sub pattern , ensuring thread safe oprn via goroutine via mutex
// now app can be scaled horizont multiple servers instances can share messages in real time via redis and broadcast them to their own connected clients
package service

import (
	"context"
	"encoding/json"
	"log"
	"sync"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/model"
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
//
// streamClients conn1, conn2, conn3, conn4 are websocket pointers
//
//	{
//	    "streamA": {
//	        conn1: true,
//	        conn2: true,
//	    },
//	    "streamB": {
//	        conn3: true,
//	        conn4: true,
//	    },
//	}
type RedisBroadcaster struct {
	clients       map[*websocket.Conn]bool            // <depracated>(broadcast-to-all)all connected clients to websocket gets the broadcast
	streamClients map[string]map[*websocket.Conn]bool // (broadcast-to-stream) clients grouped by single stream_id gets the broadcast
	mutex         sync.RWMutex                        // Mutex to ensure thread-safe access to streamClients nested map in case of multiple clients enter/exit they will be queued
	redis         *redis.Client                       // go-redis third party client type
	channel       string                              // redis channel name to subscribe to /publish on
	ctx           context.Context                     // manage goroutine cycle
	cancelFunc    context.CancelFunc                  // manage goroutine cycle
}

// NewRedisBroadcaster creates a new RedisBroadcaster and starts the subscriber goroutine
func NewRedisBroadcaster(channel string) *RedisBroadcaster {
	redisClient := myredis.GetClient()
	if redisClient == nil {
		log.Fatal("Redis client is nil! forgot to call Init!!")
	}
	ctx, cancel := context.WithCancel(context.Background())
	b := &RedisBroadcaster{
		clients:       make(map[*websocket.Conn]bool),
		streamClients: make(map[string]map[*websocket.Conn]bool),
		redis:         redisClient, // always the singleton redis client
		channel:       channel,
		ctx:           ctx,
		cancelFunc:    cancel,
	}
	go b.subscribe()
	return b
}

// <depracated> Register's/adds a new websocket client connection to the *RedisBroadcaster same instance struct
func (b *RedisBroadcaster) Register(conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	b.clients[conn] = true
	log.Printf("[WebSocket] Registered client %p. Total clients: %d", conn, len(b.clients))
}

// RegisterForStream adds a WebSocket connection to a specific stream_id group
func (b *RedisBroadcaster) RegisterForStream(streamID string, conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()

	if b.streamClients[streamID] == nil {
		b.streamClients[streamID] = make(map[*websocket.Conn]bool)
	}
	b.streamClients[streamID][conn] = true
	log.Printf("[Stream][Register] Client %p register to stream '%s'. Remaining Clients in stream: %d", conn, streamID, len(b.streamClients[streamID]))
}

// <depracated> Unregister's/remove existing websocket client connection to the *RedisBroadcaster same instance struct
func (b *RedisBroadcaster) Unregister(conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()
	delete(b.clients, conn)
	log.Printf("[WebSocket] Unregistered client %p. Total clients: %d", conn, len(b.clients))
}

// UnregisterFromStream removes a WebSocket connection from a specific stream_id group
func (b *RedisBroadcaster) UnregisterFromStream(streamID string, conn *websocket.Conn) {
	b.mutex.Lock()
	defer b.mutex.Unlock()

	if clients, ok := b.streamClients[streamID]; ok {
		delete(clients, conn)
		if len(clients) == 0 {
			delete(b.streamClients, streamID)
			log.Printf("[Stream][Unregister] All clients removed. Stream '%s' cleaned up.", streamID)
		} else {
			log.Printf("[Stream][Unregister] Client %p removed from stream '%s'. Remaining clients: %d", conn, streamID, len(clients))
		}
	}
}

// <depracated> Broadcast/publishes the message to Redis channel, Other instance will also recieve this message via redis
func (b *RedisBroadcaster) Broadcast(msg []byte) {
	log.Printf("[Broadcast] Publishing message to Redis channel '%s': %s", b.channel, string(msg))
	if err := b.redis.Publish(b.ctx, b.channel, msg).Err(); err != nil {
		log.Printf("[Broadcast] Redis publish error: %v", err)
	} else {
		log.Printf("[Broadcast] Successfully published message to Redis channel '%s'", b.channel)
	}
}

// BroadcastToStream marshals the event and publishes it to the redis channel
// It expects that event.StreamID is non-empty and valid
// fan out mech with same pub/sub approach just differs with custom payload marshalled and streamID scopes the dispatch in contrast to depracated Broadcast
func (b *RedisBroadcaster) BroadcastToStream(streamID string, event *model.Event) {
	if streamID == "" {
		log.Println("[BroadcastToStream] missing streamID. cannot publish.")
		return
	}
	event.StreamID = streamID
	// since redis is agnostic to payload hence any strucutre of data payload even custom model.Event marshalling is good to go
	payload, err := json.Marshal(event)
	if err != nil {
		log.Printf("[BroadcastToStream] failed to marshal event for stream %s: %v", streamID, err)
		return
	}

	log.Printf("[BroadcastToStream] Publishing event to stream '%s' on channel '%s': %s", streamID, b.channel, string(payload))
	if err := b.redis.Publish(b.ctx, b.channel, payload).Err(); err != nil {
		log.Printf("[BroadcastToStream] Redis publish error: %v", err)
	}
}

// subscribe listens to the redis channel and forwards messages to all connected websocket clients
func (b *RedisBroadcaster) subscribe() {
	pubsub := b.redis.Subscribe(b.ctx, b.channel)
	defer pubsub.Close()

	ch := pubsub.Channel()

	log.Printf("[Redis] Subscribed to channel '%s'", b.channel)

	for {
		select {
		case <-b.ctx.Done(): // waits for channel to close i.e ctx.Done() to shut down goroutines
			log.Println("[Redis] Subscription goroutine shutting down")
			return
		case msg, ok := <-ch:
			if !ok { // ok will be false if the channel is closed
				log.Println("[Redis] PubSub channel closed")
				return
			}
			log.Printf("[Redis] Received message from channel '%s': %s", b.channel, msg.Payload)
			// b.dispatch([]byte(msg.Payload)) //<depracated>  group dispatch msg from the channel to all local websocket clients independent of stream_id
			b.dispatchToStream([]byte(msg.Payload)) // group dispatch msg from channel to all clients of particular stream_id group
		}
	}
}

// <depracated>dispatch sends the message to all connected WebSocket clients.
func (b *RedisBroadcaster) dispatch(msg []byte) {
	var event model.Event
	if err := json.Unmarshal(msg, &event); err != nil {
		log.Printf("Invalid event format: %v", err)
		return
	}

	// 🎈 event can be processed here if needed before sending it to electron clients
	processed, _ := json.Marshal(event)

	b.mutex.Lock()
	defer b.mutex.Unlock()
	for conn := range b.clients {
		if err := conn.WriteMessage(websocket.TextMessage, processed); err != nil {
			log.Printf("[WebSocket] Failed to send message to client %p: %v. Removing client.", conn, err)
			conn.Close()
			delete(b.clients, conn) // on failed conn that websocket client is removed
		} else {
			log.Printf("[WebSocket] Sent message to client %p: %s", conn, string(msg))
		}
	}
}

// dispatchToStream sends the message to websocket clients subscribed to specific stream id
func (b *RedisBroadcaster) dispatchToStream(msg []byte) {
	var event model.Event
	if err := json.Unmarshal(msg, &event); err != nil {
		log.Printf("[DispatchToStream] Invalid event format: %v", err)
		return
	}

	if event.StreamID == "" {
		log.Printf("[DispatchToStream] missing stream_id in event. skipping...")
		return
	}

	// safely read the streams connection map so that no write occurs during this time
	b.mutex.RLock()
	conns, exists := b.streamClients[event.StreamID]
	b.mutex.RUnlock()

	if !exists || len(conns) == 0 {
		log.Printf("[DispatchToStream] No clients found for stream '%s'", event.StreamID)
		return
	}

	// 🎈 further enrich/process/validate event before broadcasting
	processed, _ := json.Marshal(event)

	// send message to all clients of that stream
	for conn := range conns {
		if err := conn.WriteMessage(websocket.TextMessage, processed); err != nil {
			log.Printf("[DispatchToStream] Failed to send to client %p: %v. Removing client.", conn, err)

			// cleanup broken connections
			b.UnregisterFromStream(event.StreamID, conn)
			conn.Close()
		} else {
			log.Printf("[DispatchToStream] Sent to client %p in stream: %s", conn, event.StreamID)
		}
	}
}

// Close stops the Redis subscription.
func (b *RedisBroadcaster) Close() {
	b.cancelFunc() // cancels/cleanup the background subscribe() goroutine
	log.Println("[Redis] Broadcaster closed")
}
