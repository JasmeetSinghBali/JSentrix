// streaming-hub/internal/config/config.go
// Package config loads configurations from environment variables and .env file
package config

import (
	"log"
	"os"
	"sync"

	"github.com/joho/godotenv"
)

// Config: holds all application configuration from .env
type Config struct {
	Port             string
	RedisAddr        string
	RedisPassword    string
	RedisChannelName string
	KafkaBrokers     string
	KafkaIngestTopic string
	// Add other fields here
}

var (
	cfg  *Config
	once sync.Once
)

// getEnv gets an environment variable or returns a default
func getEnv(key, defaultValue string) string {
	value, exists := os.LookupEnv(key)
	if !exists {
		return defaultValue
	}
	return value
}

// Load loads environment variables from a .env file (if present) and OS environment.
// It returns a Config struct with populated values.
func Load() *Config {
	// once.Do ensures the callback func() only runs once in lifetime of the fiber app even if Load() is called 100 times from differ places or goroutines to ensure singleton pattern in thread safe pattern
	once.Do(func() {
		// Load .env file if it exists
		if err := godotenv.Load(); err != nil {
			log.Println("No .env file found or error loading .env: ", err)
		}

		cfg = &Config{
			Port:             getEnv("PORT", "4001"),
			RedisAddr:        getEnv("REDIS_ADDR", "localhost:6379"),
			RedisPassword:    getEnv("REDIS_PASSWORD", ""),
			RedisChannelName: getEnv("REDIS_CHANNEL_NAME", "triageevents"),
			KafkaBrokers:     getEnv("KAFKA_BROKERS", "localhost:9092"),
			KafkaIngestTopic: getEnv("KAFKA_TOPIC", "ingest_topic"),
			// Add other fields here
		}
	})
	return cfg
}
