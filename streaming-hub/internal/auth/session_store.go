// streaming-hub/internal/auth/session_store.go
package auth

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"time"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/redis"
	"github.com/google/uuid"
)

const redisPrefix = "clientstreamhubwstokens:"

// Generate a new clientId and token, store in redis with ttl
func NewSession(ttl time.Duration) (clientId, token string, err error) {
	clientId = uuid.NewString()
	b := make([]byte, 32)
	if _, err = rand.Read(b); err != nil {
		return "", "", err
	}
	token = hex.EncodeToString(b)
	rdb := redis.GetClient()
	if err = rdb.Set(context.Background(), redisPrefix+clientId, token, ttl).Err(); err != nil {
		return "", "", err
	}
	return clientId, token, nil
}

// Validate clientId/token pair
func ValidateSession(clientId, token string) bool {
	rdb := redis.GetClient()
	stored, err := rdb.Get(context.Background(), redisPrefix+clientId).Result()
	return err == nil && stored == token
}

// Delete session on disconnect or shutdown
func DeleteSession(clientId string) error {
	rdb := redis.GetClient()
	return rdb.Del(context.Background(), redisPrefix+clientId).Err()
}

// GetTTL returns the TTL (in seconds) for a given clientId/token session
func GetTTL(clientId string) (time.Duration, error) {
	rdb := redis.GetClient()
	return rdb.TTL(context.Background(), redisPrefix+clientId).Result()
}
