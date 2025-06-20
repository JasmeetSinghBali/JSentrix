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

	// ---- KAFKA CONSUMER SETUP ----
	kafkaGroup := "streaming-hub-group"
	kafkaConsumer, err := service.NewKafkaConsumer(cfg.KafkaBrokers, kafkaGroup, cfg.KafkaIngestTopic)
	if err != nil {
		log.Fatalf("Failed to create Kafka consumer: %v", err)
	}
	// Context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	// Start Kafka consumer in a goroutine
	go func() {
		if err := kafkaConsumer.StartConsuming(ctx, broadcaster); err != nil {
			log.Fatalf("Kafka consumer error: %v", err)
		}
	}()

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
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	if err := app.ShutdownWithContext(shutdownCtx); err != nil {
		log.Printf("streaming-hub shutdown error: %v", err)
	}

	// signal kafka consumer to stop
	cancel()
	time.Sleep(1 * time.Second) // give some time for kafka consumer to close

	// Graceful shutdown: close Redis subscription
	broadcaster.Close()
	log.Println("streaming-hub exited gracefully.")
}
