// streaming-hub/internal/model/event.go
// Package model defines the event/message structure used for streaming.
package model

import "encoding/json"

// Event represents a log/event/process message to be streamed to clients.
// swagger:model Event
type Event struct {
	EventType string          `json:"event" example:"log"`
	Message   string          `json:"message" example:"Processing started"`
	StreamID  string          `json:"stream_id" example:"123e4567-e89b-12d3-..."`
	Data      json.RawMessage `json:"data,omitempty"` // to allow arbitary payloads in data
	// timestamp, agent and other fields could be added
}
