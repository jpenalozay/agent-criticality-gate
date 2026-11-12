// Main entry point for Go services
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/jlpy/chatbot/agentes/go/eventbus"
	"github.com/jlpy/chatbot/agentes/go/gitea"
	"github.com/jlpy/chatbot/agentes/go/server"
	"github.com/jlpy/chatbot/agentes/go/state"
	"gopkg.in/yaml.v3"
)

// Config represents the application configuration
type Config struct {
	NATS struct {
		URL string `yaml:"url"`
	} `yaml:"nats"`

	Redis struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		Password string `yaml:"password"`
		DB       int    `yaml:"db"`
		TTL      int    `yaml:"ttl"`
	} `yaml:"redis"`

	Postgres struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		User     string `yaml:"user"`
		Password string `yaml:"password"`
		Database string `yaml:"database"`
		SSLMode  string `yaml:"sslmode"`
	} `yaml:"postgres"`

	Gitea struct {
		BaseURL    string `yaml:"base_url"`
		Token      string `yaml:"token"`
		Owner      string `yaml:"owner"`
		Repo       string `yaml:"repo"`
		WebhookURL string `yaml:"webhook_url"`
	} `yaml:"gitea"`

	GRPC struct {
		Port int `yaml:"port"`
	} `yaml:"grpc"`
}

func main() {
	log.Println("🚀 Starting Framework Go Services...")

	// Load configuration
	cfg, err := loadConfig("config/go_services.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize Event Bus
	log.Println("Connecting to NATS...")
	eb, err := eventbus.New(cfg.NATS.URL)
	if err != nil {
		log.Fatalf("Failed to create event bus: %v", err)
	}
	defer eb.Close()

	// Initialize State Manager
	log.Println("Connecting to Redis and Postgres...")
	redisAddr := fmt.Sprintf("%s:%d", cfg.Redis.Host, cfg.Redis.Port)
	pgConnStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		cfg.Postgres.Host, cfg.Postgres.Port, cfg.Postgres.User,
		cfg.Postgres.Password, cfg.Postgres.Database, cfg.Postgres.SSLMode)

	sm, err := state.New(redisAddr, cfg.Redis.Password, cfg.Redis.DB, pgConnStr, cfg.Redis.TTL)
	if err != nil {
		log.Fatalf("Failed to create state manager: %v", err)
	}
	defer sm.Close()

	// Initialize Gitea client
	var giteaClient *gitea.Client
	if cfg.Gitea.Token != "" {
		log.Println("Connecting to Gitea...")
		giteaClient = gitea.New(cfg.Gitea.BaseURL, cfg.Gitea.Token)

		// Setup webhook if needed
		if cfg.Gitea.WebhookURL != "" {
			ctx := context.Background()
			events := []string{"push", "pull_request"}
			if err := giteaClient.CreateWebhook(ctx, cfg.Gitea.Owner, cfg.Gitea.Repo, cfg.Gitea.WebhookURL, events); err != nil {
				log.Printf("Warning: Failed to create webhook (may already exist): %v", err)
			}
		}
	} else {
		log.Println("⚠️  Gitea token not configured, skipping Gitea integration")
	}

	// Subscribe to events
	log.Println("Setting up event subscriptions...")
	setupEventSubscriptions(eb, sm)

	// Start HTTP server
	srv := server.New(&server.Config{
		EventBus:     eb,
		StateManager: sm,
		GiteaClient:  giteaClient,
		GiteaOwner:   cfg.Gitea.Owner,
		GiteaRepo:    cfg.Gitea.Repo,
	})

	// Handle graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
		<-sigChan
		log.Println("Shutting down...")
		os.Exit(0)
	}()

	// Start server
	port := 8080
	log.Printf("Starting HTTP server on port %d...", port)
	if err := srv.Start(port); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

// loadConfig loads configuration from YAML file
func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	return &cfg, nil
}

// setupEventSubscriptions sets up event handlers
func setupEventSubscriptions(eb *eventbus.EventBus, sm *state.StateManager) {
	// Subscribe to document events
	eb.Subscribe("document.>", func(event *types.Event) error {
		log.Printf("📄 Document event: %s - %s", event.Type, event.ID)
		// Here you would trigger agent actions based on document changes
		return nil
	})

	// Subscribe to task events
	eb.Subscribe("task.>", func(event *types.Event) error {
		log.Printf("📋 Task event: %s - %s", event.Type, event.ID)
		return nil
	})
}
