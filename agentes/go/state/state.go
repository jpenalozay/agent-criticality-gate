// Package state provides state management with Redis (hot) and Postgres (cold)
package state

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/jlpy/chatbot/agentes/go/types"
	_ "github.com/lib/pq"
)

// StateManager manages task state with Redis (hot) and Postgres (cold)
type StateManager struct {
	redis *redis.Client
	pg    *sql.DB
	ttl   time.Duration
}

// New creates a new StateManager
func New(redisAddr string, redisPassword string, redisDB int, pgConnStr string, ttl int) (*StateManager, error) {
	// Connect to Redis
	rdb := redis.NewClient(&redis.Options{
		Addr:     redisAddr,
		Password: redisPassword,
		DB:       redisDB,
	})

	// Test Redis connection
	ctx := context.Background()
	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}
	log.Println("Connected to Redis")

	// Connect to Postgres
	pg, err := sql.Open("postgres", pgConnStr)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Postgres: %w", err)
	}

	// Test Postgres connection
	if err := pg.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping Postgres: %w", err)
	}
	log.Println("Connected to Postgres")

	sm := &StateManager{
		redis: rdb,
		pg:    pg,
		ttl:   time.Duration(ttl) * time.Second,
	}

	// Initialize Postgres schema
	if err := sm.initializeSchema(); err != nil {
		return nil, fmt.Errorf("failed to initialize schema: %w", err)
	}

	// Start archiver worker
	go sm.archiverWorker()

	return sm, nil
}

// initializeSchema creates the required Postgres tables
func (sm *StateManager) initializeSchema() error {
	schema := `
	CREATE TABLE IF NOT EXISTS tasks (
		id TEXT PRIMARY KEY,
		status TEXT NOT NULL,
		requirement TEXT,
		blueprint JSONB,
		risk_score FLOAT,
		code TEXT,
		created_at TIMESTAMP NOT NULL,
		updated_at TIMESTAMP NOT NULL,
		metadata JSONB
	);

	CREATE TABLE IF NOT EXISTS events (
		id TEXT PRIMARY KEY,
		type TEXT NOT NULL,
		source TEXT NOT NULL,
		timestamp TIMESTAMP NOT NULL,
		data JSONB,
		metadata JSONB
	);

	CREATE TABLE IF NOT EXISTS audit_log (
		id TEXT PRIMARY KEY,
		timestamp TIMESTAMP NOT NULL,
		actor TEXT NOT NULL,
		action TEXT NOT NULL,
		resource TEXT NOT NULL,
		details JSONB,
		checksum TEXT NOT NULL
	);

	CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
	CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
	CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
	CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
	CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
	`

	_, err := sm.pg.Exec(schema)
	if err != nil {
		return fmt.Errorf("failed to create schema: %w", err)
	}

	log.Println("Postgres schema initialized")
	return nil
}

// CreateTask creates a new task in Redis (hot storage)
func (sm *StateManager) CreateTask(ctx context.Context, task *types.Task) error {
	// Set timestamps
	now := time.Now()
	task.CreatedAt = now
	task.UpdatedAt = now

	// Serialize task
	data, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("failed to marshal task: %w", err)
	}

	// Store in Redis with TTL
	key := fmt.Sprintf("task:%s", task.ID)
	if err := sm.redis.Set(ctx, key, data, sm.ttl).Err(); err != nil {
		return fmt.Errorf("failed to store task in Redis: %w", err)
	}

	// Add to pending archive queue
	if err := sm.redis.LPush(ctx, "archive:queue", task.ID).Err(); err != nil {
		log.Printf("Failed to add task to archive queue: %v", err)
	}

	log.Printf("Created task %s in Redis", task.ID)
	return nil
}

// GetTask retrieves a task from Redis (or Postgres if not in Redis)
func (sm *StateManager) GetTask(ctx context.Context, taskID string) (*types.Task, error) {
	// Try Redis first (hot storage)
	key := fmt.Sprintf("task:%s", taskID)
	data, err := sm.redis.Get(ctx, key).Bytes()
	if err == nil {
		var task types.Task
		if err := json.Unmarshal(data, &task); err != nil {
			return nil, fmt.Errorf("failed to unmarshal task: %w", err)
		}
		return &task, nil
	}

	// If not in Redis, try Postgres (cold storage)
	if err != redis.Nil {
		log.Printf("Redis error: %v", err)
	}

	var task types.Task
	var blueprintJSON, metadataJSON []byte
	err = sm.pg.QueryRowContext(ctx, `
		SELECT id, status, requirement, blueprint, risk_score, code, created_at, updated_at, metadata
		FROM tasks WHERE id = $1
	`, taskID).Scan(
		&task.ID, &task.Status, &task.Requirement, &blueprintJSON,
		&task.RiskScore, &task.Code, &task.CreatedAt, &task.UpdatedAt, &metadataJSON,
	)

	if err == sql.ErrNoRows {
		return nil, fmt.Errorf("task not found: %s", taskID)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to query task from Postgres: %w", err)
	}

	// Unmarshal JSON fields
	if len(blueprintJSON) > 0 {
		json.Unmarshal(blueprintJSON, &task.Blueprint)
	}
	if len(metadataJSON) > 0 {
		json.Unmarshal(metadataJSON, &task.Metadata)
	}

	// Cache in Redis for future requests
	taskData, _ := json.Marshal(task)
	sm.redis.Set(ctx, key, taskData, sm.ttl)

	return &task, nil
}

// UpdateTask updates a task in Redis
func (sm *StateManager) UpdateTask(ctx context.Context, task *types.Task) error {
	task.UpdatedAt = time.Now()

	data, err := json.Marshal(task)
	if err != nil {
		return fmt.Errorf("failed to marshal task: %w", err)
	}

	key := fmt.Sprintf("task:%s", task.ID)
	if err := sm.redis.Set(ctx, key, data, sm.ttl).Err(); err != nil {
		return fmt.Errorf("failed to update task in Redis: %w", err)
	}

	// Add to archive queue
	sm.redis.LPush(ctx, "archive:queue", task.ID)

	log.Printf("Updated task %s in Redis", task.ID)
	return nil
}

// ListTasks lists all tasks (from Redis and Postgres)
func (sm *StateManager) ListTasks(ctx context.Context, limit int) ([]*types.Task, error) {
	var tasks []*types.Task

	// Get from Postgres (authoritative source)
	rows, err := sm.pg.QueryContext(ctx, `
		SELECT id, status, requirement, blueprint, risk_score, code, created_at, updated_at, metadata
		FROM tasks
		ORDER BY created_at DESC
		LIMIT $1
	`, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query tasks: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var task types.Task
		var blueprintJSON, metadataJSON []byte
		err := rows.Scan(
			&task.ID, &task.Status, &task.Requirement, &blueprintJSON,
			&task.RiskScore, &task.Code, &task.CreatedAt, &task.UpdatedAt, &metadataJSON,
		)
		if err != nil {
			log.Printf("Failed to scan task: %v", err)
			continue
		}

		if len(blueprintJSON) > 0 {
			json.Unmarshal(blueprintJSON, &task.Blueprint)
		}
		if len(metadataJSON) > 0 {
			json.Unmarshal(metadataJSON, &task.Metadata)
		}

		tasks = append(tasks, &task)
	}

	return tasks, nil
}

// archiverWorker archives tasks from Redis to Postgres asynchronously
func (sm *StateManager) archiverWorker() {
	ctx := context.Background()
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	log.Println("Archiver worker started")

	for range ticker.C {
		// Process archive queue
		for {
			taskID, err := sm.redis.RPop(ctx, "archive:queue").Result()
			if err == redis.Nil {
				break // Queue empty
			}
			if err != nil {
				log.Printf("Archive queue error: %v", err)
				break
			}

			// Get task from Redis
			task, err := sm.GetTask(ctx, taskID)
			if err != nil {
				log.Printf("Failed to get task %s for archiving: %v", taskID, err)
				continue
			}

			// Archive to Postgres
			if err := sm.archiveTask(ctx, task); err != nil {
				log.Printf("Failed to archive task %s: %v", taskID, err)
				// Re-add to queue for retry
				sm.redis.LPush(ctx, "archive:queue", taskID)
			}
		}
	}
}

// archiveTask archives a task to Postgres
func (sm *StateManager) archiveTask(ctx context.Context, task *types.Task) error {
	blueprintJSON, _ := json.Marshal(task.Blueprint)
	metadataJSON, _ := json.Marshal(task.Metadata)

	_, err := sm.pg.ExecContext(ctx, `
		INSERT INTO tasks (id, status, requirement, blueprint, risk_score, code, created_at, updated_at, metadata)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		ON CONFLICT (id) DO UPDATE SET
			status = EXCLUDED.status,
			blueprint = EXCLUDED.blueprint,
			risk_score = EXCLUDED.risk_score,
			code = EXCLUDED.code,
			updated_at = EXCLUDED.updated_at,
			metadata = EXCLUDED.metadata
	`, task.ID, task.Status, task.Requirement, blueprintJSON, task.RiskScore,
		task.Code, task.CreatedAt, task.UpdatedAt, metadataJSON)

	if err != nil {
		return fmt.Errorf("failed to insert/update task in Postgres: %w", err)
	}

	log.Printf("Archived task %s to Postgres", task.ID)
	return nil
}

// Close closes connections
func (sm *StateManager) Close() {
	if sm.redis != nil {
		sm.redis.Close()
	}
	if sm.pg != nil {
		sm.pg.Close()
	}
	log.Println("StateManager closed")
}
