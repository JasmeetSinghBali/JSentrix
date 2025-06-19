// streaming-hub/internal/redis/redis.go
package redis

import (
	"context"
	"sync"
	"time"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/config"
	"github.com/redis/go-redis/v9"
)

// RedisClient: global redis client instance
var (
	redisClient *redis.Client
	redisOnce   sync.Once
	initError   error
)

// GetClient: returns the singleton redis client instance
func GetClient() *redis.Client {
	return redisClient
}

// InitRedis: initializes the Redis client with env variables
func Init(cfg *config.Config) error {
	redisOnce.Do(func() {
		client := redis.NewClient(&redis.Options{
			Addr:     cfg.RedisAddr,
			Password: cfg.RedisPassword,
			DB:       0,
		})

		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		if err := client.Ping(ctx).Err(); err != nil {
			initError = err
			return
		}

		redisClient = client
	})
	return initError
}
