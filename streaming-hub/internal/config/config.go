// streaming-hub/internal/config/config.go
// Package config loads configurations from environment variables and .env file
package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Port string
}

// Load loads environment variables from a .env file (if present) and OS environment.
// It returns a Config struct with populated values.
func Load() *Config {
	// Load .env file if it exists (does not override OS env vars)
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found or error loading .env: ", err)
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "3000"
	}
	return &Config{Port: ":" + port}
}
