// streaming-hub/internal/utils/kafka.go
package utils

import (
	"context"
	"log"
	"time"

	"github.com/confluentinc/confluent-kafka-go/kafka"
)

// EnsureKafkaTopics ensures all specified topics exist or creates them if missing.
func EnsureKafkaTopics(brokers string, topics []string) {
	admin, err := kafka.NewAdminClient(&kafka.ConfigMap{
		"bootstrap.servers": brokers,
	})
	if err != nil {
		log.Fatalf("❌ Kafka Admin client failed: %v", err)
	}
	defer admin.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	meta, err := admin.GetMetadata(nil, false, 5000)
	if err != nil {
		log.Fatalf("⚠️ Could not fetch Kafka metadata: %v", err)
	}

	var toCreate []kafka.TopicSpecification
	for _, topic := range topics {
		if _, exists := meta.Topics[topic]; exists {
			log.Printf("✅ Kafka topic '%s' already exists", topic)
			continue
		}
		toCreate = append(toCreate, kafka.TopicSpecification{
			Topic:             topic,
			NumPartitions:     1,
			ReplicationFactor: 1,
		})
	}

	if len(toCreate) == 0 {
		return
	}

	results, err := admin.CreateTopics(ctx, toCreate)
	if err != nil {
		log.Printf("⚠️ Kafka topic creation error: %v", err)
		return
	}

	for _, res := range results {
		if res.Error.Code() == kafka.ErrNoError || res.Error.Code() == kafka.ErrTopicAlreadyExists {
			log.Printf("✅ Kafka topic '%s' ensured: %s", res.Topic, res.Error.String())
		} else {
			log.Fatalf("❌ Kafka topic creation failed: %s", res.Error.String())
		}
	}
}
