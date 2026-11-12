// Package eventbus provides NATS JetStream event bus implementation
package eventbus

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/jlpy/chatbot/agentes/go/types"
	"github.com/nats-io/nats.go"
)

// EventBus handles event publishing and subscription using NATS JetStream
type EventBus struct {
	nc *nats.Conn
	js nats.JetStreamContext
}

// New creates a new EventBus instance
func New(url string) (*EventBus, error) {
	// Connect to NATS
	nc, err := nats.Connect(url,
		nats.MaxReconnects(10),
		nats.ReconnectWait(2*time.Second),
		nats.DisconnectErrHandler(func(nc *nats.Conn, err error) {
			log.Printf("NATS disconnected: %v", err)
		}),
		nats.ReconnectHandler(func(nc *nats.Conn) {
			log.Printf("NATS reconnected to %s", nc.ConnectedUrl())
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to NATS: %w", err)
	}

	// Create JetStream context
	js, err := nc.JetStream()
	if err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to create JetStream context: %w", err)
	}

	eb := &EventBus{
		nc: nc,
		js: js,
	}

	// Initialize streams
	if err := eb.initializeStreams(); err != nil {
		nc.Close()
		return nil, fmt.Errorf("failed to initialize streams: %w", err)
	}

	return eb, nil
}

// initializeStreams creates the required JetStream streams
func (eb *EventBus) initializeStreams() error {
	streams := []struct {
		name     string
		subjects []string
	}{
		{
			name:     "EVENTS",
			subjects: []string{"event.>"},
		},
		{
			name:     "TASKS",
			subjects: []string{"task.>"},
		},
		{
			name:     "DOCUMENTS",
			subjects: []string{"document.>"},
		},
	}

	for _, stream := range streams {
		// Check if stream exists
		_, err := eb.js.StreamInfo(stream.name)
		if err == nil {
			log.Printf("Stream %s already exists", stream.name)
			continue
		}

		// Create stream
		_, err = eb.js.AddStream(&nats.StreamConfig{
			Name:       stream.name,
			Subjects:   stream.subjects,
			Retention:  nats.LimitsPolicy,
			MaxAge:     7 * 24 * time.Hour, // 7 days retention
			Storage:    nats.FileStorage,
			Replicas:   1, // Change to 3 for production cluster
			Duplicates: 5 * time.Minute,
		})
		if err != nil {
			return fmt.Errorf("failed to create stream %s: %w", stream.name, err)
		}
		log.Printf("Created stream: %s", stream.name)
	}

	return nil
}

// Publish publishes an event to the event bus
func (eb *EventBus) Publish(ctx context.Context, subject string, event *types.Event) error {
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	// Publish with context
	_, err = eb.js.Publish(subject, data, nats.Context(ctx))
	if err != nil {
		return fmt.Errorf("failed to publish event: %w", err)
	}

	log.Printf("Published event %s to %s", event.ID, subject)
	return nil
}

// PublishAsync publishes an event asynchronously
func (eb *EventBus) PublishAsync(subject string, event *types.Event) error {
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}

	// Async publish
	_, err = eb.js.PublishAsync(subject, data)
	if err != nil {
		return fmt.Errorf("failed to publish event async: %w", err)
	}

	return nil
}

// Subscribe subscribes to events on a subject
func (eb *EventBus) Subscribe(subject string, handler func(*types.Event) error) error {
	_, err := eb.js.Subscribe(subject, func(msg *nats.Msg) {
		var event types.Event
		if err := json.Unmarshal(msg.Data, &event); err != nil {
			log.Printf("Failed to unmarshal event: %v", err)
			msg.Nak() // Negative acknowledgment
			return
		}

		// Handle event
		if err := handler(&event); err != nil {
			log.Printf("Handler error for event %s: %v", event.ID, err)
			msg.Nak()
			return
		}

		// Acknowledge successful processing
		msg.Ack()
	}, nats.Durable("durable-"+subject), nats.ManualAck())

	if err != nil {
		return fmt.Errorf("failed to subscribe to %s: %w", subject, err)
	}

	log.Printf("Subscribed to: %s", subject)
	return nil
}

// QueueSubscribe subscribes with a queue group for load balancing
func (eb *EventBus) QueueSubscribe(subject, queue string, handler func(*types.Event) error) error {
	_, err := eb.js.QueueSubscribe(subject, queue, func(msg *nats.Msg) {
		var event types.Event
		if err := json.Unmarshal(msg.Data, &event); err != nil {
			log.Printf("Failed to unmarshal event: %v", err)
			msg.Nak()
			return
		}

		if err := handler(&event); err != nil {
			log.Printf("Handler error for event %s: %v", event.ID, err)
			msg.Nak()
			return
		}

		msg.Ack()
	}, nats.Durable("durable-"+queue), nats.ManualAck())

	if err != nil {
		return fmt.Errorf("failed to queue subscribe to %s: %w", subject, err)
	}

	log.Printf("Queue subscribed to: %s (queue: %s)", subject, queue)
	return nil
}

// Close closes the NATS connection
func (eb *EventBus) Close() {
	if eb.nc != nil {
		eb.nc.Close()
		log.Println("EventBus closed")
	}
}

// GetStats returns statistics about the event bus
func (eb *EventBus) GetStats() (map[string]interface{}, error) {
	stats := make(map[string]interface{})

	// Get stream info for all streams
	streams := []string{"EVENTS", "TASKS", "DOCUMENTS"}
	for _, streamName := range streams {
		info, err := eb.js.StreamInfo(streamName)
		if err != nil {
			continue
		}

		stats[streamName] = map[string]interface{}{
			"messages": info.State.Msgs,
			"bytes":    info.State.Bytes,
			"first_seq": info.State.FirstSeq,
			"last_seq":  info.State.LastSeq,
		}
	}

	return stats, nil
}
