// streaming-hub/internal/service/kafka_consumer.go
// Package service provides Kafka consumer logic for event streaming.
package service

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/JasmeetSinghBali/JSentrix/streaming-hub/internal/model"
	"github.com/confluentinc/confluent-kafka-go/kafka"
)

// KafkaConsumer wraps a Sarama consumer group for robust consumption
type KafkaConsumer struct {
	consumer *kafka.Consumer
	topic    string
}

// NewKafkaConsumer creates a new Kafka consumer.
func NewKafkaConsumer(brokers, groupID, topic string) (*KafkaConsumer, error) {
	c, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": brokers,
		"group.id":          groupID,
		"auto.offset.reset": "earliest",
	})
	if err != nil {
		return nil, err
	}
	return &KafkaConsumer{consumer: c, topic: topic}, nil
}

// StartConsuming runs the consumer loop and broadcasts messages to all clients.
func (kc *KafkaConsumer) StartConsuming(ctx context.Context, broadcaster *RedisBroadcaster) error {
	err := kc.consumer.SubscribeTopics([]string{kc.topic}, nil)
	if err != nil {
		return err
	}
	log.Printf("Kafka consumer subscribed to topic: %s", kc.topic)

	run := true
	sigchan := make(chan os.Signal, 1)
	signal.Notify(sigchan, syscall.SIGINT, syscall.SIGTERM)

	for run {
		select {
		case <-ctx.Done():
			run = false
		case sig := <-sigchan:
			log.Printf("Received signal %v: shutting down Kafka consumer", sig)
			run = false
		default:
			ev := kc.consumer.Poll(100)
			if ev == nil {
				continue
			}
			switch e := ev.(type) {
			case *kafka.Message:
				var event model.Event
				if err := json.Unmarshal(e.Value, &event); err != nil {
					log.Printf("Failed to parse event: %v", err)
				} else {
					log.Printf("Received Kafka message: %s", string(e.Value))
					// Broadcast the raw event to all websocket clients(electron)
					broadcaster.Broadcast(e.Value)
					log.Printf("Broadcasted event to WebSocket clients: %s", string(e.Value))
				}
			case kafka.Error:
				log.Printf("Kafka error: %v", e)
			}
		}
	}
	log.Println("Closing Kafka consumer...")
	kc.consumer.Close()
	return nil
}
