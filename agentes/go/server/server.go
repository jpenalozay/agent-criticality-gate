// Package server provides the main HTTP server for webhooks and APIs
package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/jlpy/chatbot/agentes/go/eventbus"
	"github.com/jlpy/chatbot/agentes/go/gitea"
	"github.com/jlpy/chatbot/agentes/go/state"
	"github.com/jlpy/chatbot/agentes/go/types"
)

// Server is the main HTTP server
type Server struct {
	eventBus       *eventbus.EventBus
	stateManager   *state.StateManager
	giteaClient    *gitea.Client
	webhookHandler *gitea.WebhookHandler
	giteaOwner     string
	giteaRepo      string
}

// Config holds server configuration
type Config struct {
	EventBus     *eventbus.EventBus
	StateManager *state.StateManager
	GiteaClient  *gitea.Client
	GiteaOwner   string
	GiteaRepo    string
}

// New creates a new server
func New(cfg *Config) *Server {
	s := &Server{
		eventBus:     cfg.EventBus,
		stateManager: cfg.StateManager,
		giteaClient:  cfg.GiteaClient,
		giteaOwner:   cfg.GiteaOwner,
		giteaRepo:    cfg.GiteaRepo,
	}

	// Setup webhook handler
	s.webhookHandler = gitea.NewWebhookHandler()
	s.setupWebhookHandlers()

	return s
}

// setupWebhookHandlers configures webhook event handlers
func (s *Server) setupWebhookHandlers() {
	// Handle push events (document updates merged to main)
	s.webhookHandler.OnPush(func(event *gitea.WebhookEvent) error {
		log.Printf("📝 Push event: %s", event.String())

		// Check if documents were changed
		if !event.IsDocumentChange() {
			log.Println("No document changes, skipping")
			return nil
		}

		// Publish event to NATS
		ctx := context.Background()
		busEvent := &types.Event{
			ID:        uuid.New().String(),
			Type:      "document.updated",
			Source:    "gitea",
			Timestamp: time.Now(),
			Data: map[string]interface{}{
				"repository": event.Repository.FullName,
				"ref":        event.Ref,
				"files":      event.GetChangedFiles(),
				"commits":    len(event.Commits),
			},
			Metadata: map[string]string{
				"pusher": event.Pusher.Login,
			},
		}

		if err := s.eventBus.Publish(ctx, "document.updated", busEvent); err != nil {
			return fmt.Errorf("failed to publish event: %w", err)
		}

		log.Printf("✅ Published document.updated event: %s", busEvent.ID)
		return nil
	})

	// Handle pull request events (review requests)
	s.webhookHandler.OnPullRequest(func(event *gitea.WebhookEvent) error {
		log.Printf("🔍 PR event: %s - %s", event.Action, event.String())

		ctx := context.Background()
		var eventType string

		switch event.Action {
		case "opened":
			eventType = "document.review_requested"
		case "synchronized":
			eventType = "document.review_updated"
		default:
			log.Printf("Unhandled PR action: %s", event.Action)
			return nil
		}

		// Publish event to NATS
		busEvent := &types.Event{
			ID:        uuid.New().String(),
			Type:      eventType,
			Source:    "gitea",
			Timestamp: time.Now(),
			Data: map[string]interface{}{
				"repository": event.Repository.FullName,
				"pr_number":  event.PullRequest.Number,
				"pr_title":   event.PullRequest.Title,
				"head_ref":   event.PullRequest.Head.Ref,
				"base_ref":   event.PullRequest.Base.Ref,
			},
			Metadata: map[string]string{
				"sender": event.Sender.Login,
			},
		}

		if err := s.eventBus.Publish(ctx, eventType, busEvent); err != nil {
			return fmt.Errorf("failed to publish event: %w", err)
		}

		log.Printf("✅ Published %s event: %s", eventType, busEvent.ID)
		return nil
	})

	// Handle merge events (PR merged)
	s.webhookHandler.OnMerge(func(event *gitea.WebhookEvent) error {
		log.Printf("✅ Merge event: %s", event.String())

		ctx := context.Background()

		// Publish event to NATS
		busEvent := &types.Event{
			ID:        uuid.New().String(),
			Type:      "document.approved",
			Source:    "gitea",
			Timestamp: time.Now(),
			Data: map[string]interface{}{
				"repository": event.Repository.FullName,
				"pr_number":  event.PullRequest.Number,
				"pr_title":   event.PullRequest.Title,
				"merged_at":  event.PullRequest.MergedAt,
			},
			Metadata: map[string]string{
				"sender": event.Sender.Login,
			},
		}

		if err := s.eventBus.Publish(ctx, "document.approved", busEvent); err != nil {
			return fmt.Errorf("failed to publish event: %w", err)
		}

		log.Printf("✅ Published document.approved event: %s", busEvent.ID)
		return nil
	})
}

// Start starts the HTTP server
func (s *Server) Start(port int) error {
	mux := http.NewServeMux()

	// Webhook endpoint
	mux.Handle("/api/webhooks/gitea", s.webhookHandler)

	// Health check
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{
			"status": "healthy",
			"time":   time.Now().Format(time.RFC3339),
		})
	})

	// Stats endpoint
	mux.HandleFunc("/api/stats", s.handleStats)

	addr := fmt.Sprintf(":%d", port)
	log.Printf("🚀 Server starting on %s", addr)

	server := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	return server.ListenAndServe()
}

// handleStats returns system statistics
func (s *Server) handleStats(w http.ResponseWriter, r *http.Request) {
	ctx := context.Background()

	stats := make(map[string]interface{})

	// Event bus stats
	if ebStats, err := s.eventBus.GetStats(); err == nil {
		stats["event_bus"] = ebStats
	}

	// Task stats
	tasks, err := s.stateManager.ListTasks(ctx, 10)
	if err == nil {
		stats["recent_tasks"] = len(tasks)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}
