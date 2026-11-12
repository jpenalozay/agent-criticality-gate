// Package types defines common types used across the Go services
package types

import (
	"time"
)

// Event represents a system event
type Event struct {
	ID        string                 `json:"id"`
	Type      string                 `json:"type"`
	Source    string                 `json:"source"`
	Timestamp time.Time              `json:"timestamp"`
	Data      map[string]interface{} `json:"data"`
	Metadata  map[string]string      `json:"metadata"`
}

// Task represents a task in the system
type Task struct {
	ID          string                 `json:"id"`
	Status      string                 `json:"status"`
	Requirement string                 `json:"requirement"`
	Blueprint   map[string]interface{} `json:"blueprint,omitempty"`
	RiskScore   float64                `json:"risk_score,omitempty"`
	Code        string                 `json:"code,omitempty"`
	CreatedAt   time.Time              `json:"created_at"`
	UpdatedAt   time.Time              `json:"updated_at"`
	Metadata    map[string]string      `json:"metadata"`
}

// Document represents a stored document
type Document struct {
	ID          string            `json:"id"`
	Type        string            `json:"type"`
	TaskID      string            `json:"task_id"`
	Content     []byte            `json:"content"`
	Version     int               `json:"version"`
	Tags        []string          `json:"tags"`
	Metadata    map[string]string `json:"metadata"`
	CreatedAt   time.Time         `json:"created_at"`
	UpdatedAt   time.Time         `json:"updated_at"`
	StoragePath string            `json:"storage_path"`
}

// AuditEntry represents an audit log entry
type AuditEntry struct {
	ID        string                 `json:"id"`
	Timestamp time.Time              `json:"timestamp"`
	Actor     string                 `json:"actor"`
	Action    string                 `json:"action"`
	Resource  string                 `json:"resource"`
	Details   map[string]interface{} `json:"details"`
	Checksum  string                 `json:"checksum"`
}

// RiskAssessment represents a risk evaluation
type RiskAssessment struct {
	TaskID          string             `json:"task_id"`
	Score           float64            `json:"score"`
	Level           string             `json:"level"`
	Impact          float64            `json:"impact"`
	Complexity      float64            `json:"complexity"`
	Sensitivity     float64            `json:"sensitivity"`
	Recommendations []string           `json:"recommendations"`
	Timestamp       time.Time          `json:"timestamp"`
	Metadata        map[string]float64 `json:"metadata"`
}

// Config represents the system configuration
type Config struct {
	NATS struct {
		URL         string   `yaml:"url"`
		ClusterURLs []string `yaml:"cluster_urls"`
		MaxReconnect int     `yaml:"max_reconnect"`
	} `yaml:"nats"`

	Redis struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		Password string `yaml:"password"`
		DB       int    `yaml:"db"`
		TTL      int    `yaml:"ttl"` // seconds
	} `yaml:"redis"`

	Postgres struct {
		Host     string `yaml:"host"`
		Port     int    `yaml:"port"`
		User     string `yaml:"user"`
		Password string `yaml:"password"`
		Database string `yaml:"database"`
		SSLMode  string `yaml:"sslmode"`
	} `yaml:"postgres"`

	MinIO struct {
		Endpoint  string `yaml:"endpoint"`
		AccessKey string `yaml:"access_key"`
		SecretKey string `yaml:"secret_key"`
		UseSSL    bool   `yaml:"use_ssl"`
		Bucket    string `yaml:"bucket"`
	} `yaml:"minio"`

	GRPC struct {
		Port int `yaml:"port"`
	} `yaml:"grpc"`
}
