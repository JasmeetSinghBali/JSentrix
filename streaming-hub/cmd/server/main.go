// @title           Streaming Hub API
// @version         1.0
// @description     Real-time log/event streaming microservice for MCP/Electron.
// @contact.name    Jasmeet Singh Bali
// @contact.email   jasmeetbali.dev.2021@gmail.com
// @host            localhost:4001
// @BasePath        /
package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/config"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/delivery/http"
	myredis "github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/redis"
	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/service"
)

func main() {
	// Load application configurations
	cfg := config.Load()

	// Initialize redis singleton
	if err := myredis.Init(cfg); err != nil {
		log.Fatalf("Failed to initialize Redis: %v", err)
	}

	broadcaster := service.NewRedisBroadcaster(cfg.RedisChannelName)

	// Initialize fiber app
	app := http.NewFiberApp(cfg, broadcaster)

	// channel to listen to interupt/terminate signals
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	// Start server in goroutine
	go func() {
		log.Printf("Starting server on %s", cfg.Port)
		port := cfg.Port
		if !strings.HasPrefix(port, ":") {
			port = ":" + port
		}
		if err := app.Listen(port); err != nil {
			log.Fatalf("streaming-hub failed to start: %v", err)
		}
	}()

	// wait for shutdown signal
	<-quit
	log.Println("Shutting down streaming-hub...")

	// gracefull shutdown fiber with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := app.ShutdownWithContext(ctx); err != nil {
		log.Printf("streaming-hub shutdown error: %v", err)
	}

	// Graceful shutdown: close Redis subscription
	broadcaster.Close()
	log.Println("streaming-hub exited gracefully.")
}
