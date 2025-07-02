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
	Data      json.RawMessage `json:"data,omitempty"`                                     // to allow arbitary payloads in data
	Timestamp string          `json:"timestamp,omitempty" example:"2025-06-26T19:23:00Z"` //ISO 8601 timestamp
	Agent     string          `json:"agent,omitempty" example:"parser-service"`           // optional sender identity
	Level     string          `json:"level,omitempty" example:"info"`
	Flagged   bool            `json:"flagged,omitempty"`
	// other fields could be added for consumed kafka event...
}
