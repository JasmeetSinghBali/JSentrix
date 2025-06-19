// streaming-hub/test/handler_test.go
// start docker-compose to start redis instance
// npm run start mcp-client
// go run cmd/server/main.go to startup streaming-hub
// then go test test/handler_test.go
// shud get event broadcasted and displayed inside the electron ui
package test

import (
	"bytes"
	"io"
	"net/http"
	"testing"
	"time"
)

// Change this if your server runs on a different port or host
const baseURL = "http://localhost"

func TestHealthCheck_LiveServer(t *testing.T) {
	resp, err := http.Get(baseURL + "/health")
	if err != nil {
		t.Fatalf("Failed to GET /health: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}
}

func TestIngestEndpoint_LiveServer(t *testing.T) {
	body := []byte(`{"event":"log","message":"test from integration test","stream_id":"123e4567-e89b-12d3-a456-426614174000"}`)
	req, err := http.NewRequest("POST", baseURL+"/ingest", bytes.NewBuffer(body))
	if err != nil {
		t.Fatalf("Failed to create POST request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("Failed to POST /ingest: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 202 {
		b, _ := io.ReadAll(resp.Body)
		t.Errorf("Expected status 202, got %d. Body: %s", resp.StatusCode, string(b))
	}
}
