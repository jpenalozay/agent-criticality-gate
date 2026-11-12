package eventbus

import (
	"context"
	"testing"
	"time"

	"github.com/jlpy/chatbot/agentes/go/types"
	"github.com/google/uuid"
)

func TestEventBus(t *testing.T) {
	// Skip if NATS is not running
	eb, err := New("nats://localhost:4222")
	if err != nil {
		t.Skipf("Skipping test: NATS not available: %v", err)
		return
	}
	defer eb.Close()

	t.Run("PublishAndSubscribe", func(t *testing.T) {
		received := make(chan *types.Event, 1)

		// Subscribe
		err := eb.Subscribe("test.event", func(event *types.Event) error {
			received <- event
			return nil
		})
		if err != nil {
			t.Fatalf("Failed to subscribe: %v", err)
		}

		// Give subscription time to be ready
		time.Sleep(100 * time.Millisecond)

		// Publish
		testEvent := &types.Event{
			ID:        uuid.New().String(),
			Type:      "test",
			Source:    "test",
			Timestamp: time.Now(),
			Data: map[string]interface{}{
				"message": "Hello, World!",
			},
			Metadata: map[string]string{
				"test": "true",
			},
		}

		ctx := context.Background()
		err = eb.Publish(ctx, "test.event", testEvent)
		if err != nil {
			t.Fatalf("Failed to publish: %v", err)
		}

		// Wait for event
		select {
		case event := <-received:
			if event.ID != testEvent.ID {
				t.Errorf("Expected event ID %s, got %s", testEvent.ID, event.ID)
			}
			if event.Type != testEvent.Type {
				t.Errorf("Expected event type %s, got %s", testEvent.Type, event.Type)
			}
		case <-time.After(5 * time.Second):
			t.Fatal("Timeout waiting for event")
		}
	})

	t.Run("GetStats", func(t *testing.T) {
		stats, err := eb.GetStats()
		if err != nil {
			t.Fatalf("Failed to get stats: %v", err)
		}

		if stats == nil {
			t.Fatal("Stats should not be nil")
		}

		t.Logf("Stats: %+v", stats)
	})
}

func BenchmarkPublish(b *testing.B) {
	eb, err := New("nats://localhost:4222")
	if err != nil {
		b.Skipf("Skipping benchmark: NATS not available: %v", err)
		return
	}
	defer eb.Close()

	event := &types.Event{
		ID:        uuid.New().String(),
		Type:      "benchmark",
		Source:    "test",
		Timestamp: time.Now(),
		Data: map[string]interface{}{
			"index": 0,
		},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		event.ID = uuid.New().String()
		event.Data["index"] = i
		eb.PublishAsync("benchmark.event", event)
	}
}
