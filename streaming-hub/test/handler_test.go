package test

import (
	"bytes"
	"net/http/httptest"
	"testing"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/delivery/http"
)

func TestHealthCheck(t *testing.T) {
	app := http.NewFiberApp(nil)
	req := httptest.NewRequest("GET", "/health", nil)
	resp, _ := app.Test(req)
	if resp.StatusCode != 200 {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}
}

func TestIngestEndpoint(t *testing.T) {
	app := http.NewFiberApp(nil)
	body := []byte(`{"event":"log","message":"test","stream_id":"123e4567-e89b-12d3-a456-426614174000"}`)
	req := httptest.NewRequest("POST", "/ingest", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	resp, _ := app.Test(req)
	if resp.StatusCode != 202 {
		t.Errorf("Expected status 202, got %d", resp.StatusCode)
	}
}
