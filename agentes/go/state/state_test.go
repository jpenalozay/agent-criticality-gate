package state

import (
	"context"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/jlpy/chatbot/agentes/go/types"
)

func TestStateManager(t *testing.T) {
	// Skip if Redis/Postgres not running
	sm, err := New(
		"localhost:6379",
		"",
		0,
		"host=localhost port=5432 user=postgres password=postgres dbname=framework sslmode=disable",
		3600,
	)
	if err != nil {
		t.Skipf("Skipping test: Infrastructure not available: %v", err)
		return
	}
	defer sm.Close()

	t.Run("CreateAndGetTask", func(t *testing.T) {
		ctx := context.Background()

		// Create task
		task := &types.Task{
			ID:          uuid.New().String(),
			Status:      "pending",
			Requirement: "Test requirement",
			Metadata: map[string]string{
				"test": "true",
			},
		}

		err := sm.CreateTask(ctx, task)
		if err != nil {
			t.Fatalf("Failed to create task: %v", err)
		}

		// Get task
		retrieved, err := sm.GetTask(ctx, task.ID)
		if err != nil {
			t.Fatalf("Failed to get task: %v", err)
		}

		if retrieved.ID != task.ID {
			t.Errorf("Expected task ID %s, got %s", task.ID, retrieved.ID)
		}
		if retrieved.Status != task.Status {
			t.Errorf("Expected status %s, got %s", task.Status, retrieved.Status)
		}
	})

	t.Run("UpdateTask", func(t *testing.T) {
		ctx := context.Background()

		// Create task
		task := &types.Task{
			ID:          uuid.New().String(),
			Status:      "pending",
			Requirement: "Test requirement",
		}

		err := sm.CreateTask(ctx, task)
		if err != nil {
			t.Fatalf("Failed to create task: %v", err)
		}

		// Update task
		task.Status = "completed"
		task.Code = "print('Hello, World!')"
		err = sm.UpdateTask(ctx, task)
		if err != nil {
			t.Fatalf("Failed to update task: %v", err)
		}

		// Verify update
		retrieved, err := sm.GetTask(ctx, task.ID)
		if err != nil {
			t.Fatalf("Failed to get task: %v", err)
		}

		if retrieved.Status != "completed" {
			t.Errorf("Expected status completed, got %s", retrieved.Status)
		}
		if retrieved.Code != task.Code {
			t.Errorf("Expected code %s, got %s", task.Code, retrieved.Code)
		}
	})

	t.Run("ListTasks", func(t *testing.T) {
		ctx := context.Background()

		// Create multiple tasks
		for i := 0; i < 5; i++ {
			task := &types.Task{
				ID:          uuid.New().String(),
				Status:      "pending",
				Requirement: "Test requirement",
			}
			sm.CreateTask(ctx, task)
		}

		// Wait for archiver
		time.Sleep(2 * time.Second)

		// List tasks
		tasks, err := sm.ListTasks(ctx, 10)
		if err != nil {
			t.Fatalf("Failed to list tasks: %v", err)
		}

		if len(tasks) < 5 {
			t.Errorf("Expected at least 5 tasks, got %d", len(tasks))
		}
	})
}

func BenchmarkCreateTask(b *testing.B) {
	sm, err := New(
		"localhost:6379",
		"",
		0,
		"host=localhost port=5432 user=postgres password=postgres dbname=framework sslmode=disable",
		3600,
	)
	if err != nil {
		b.Skipf("Skipping benchmark: Infrastructure not available: %v", err)
		return
	}
	defer sm.Close()

	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		task := &types.Task{
			ID:          uuid.New().String(),
			Status:      "pending",
			Requirement: "Benchmark requirement",
		}
		sm.CreateTask(ctx, task)
	}
}
