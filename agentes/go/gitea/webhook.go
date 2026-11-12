// Package gitea provides webhook handling for Gitea events
package gitea

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

// WebhookEvent represents a Gitea webhook event
type WebhookEvent struct {
	Action     string          `json:"action"`
	Number     int64           `json:"number"`
	Repository WebhookRepo     `json:"repository"`
	PullRequest *WebhookPR     `json:"pull_request,omitempty"`
	Pusher     WebhookUser     `json:"pusher,omitempty"`
	Sender     WebhookUser     `json:"sender"`
	Ref        string          `json:"ref"`
	Before     string          `json:"before"`
	After      string          `json:"after"`
	Commits    []WebhookCommit `json:"commits,omitempty"`
}

// WebhookRepo represents repository info in webhook
type WebhookRepo struct {
	ID       int64  `json:"id"`
	Name     string `json:"name"`
	FullName string `json:"full_name"`
	Owner    WebhookUser `json:"owner"`
}

// WebhookUser represents user info in webhook
type WebhookUser struct {
	ID       int64  `json:"id"`
	Login    string `json:"login"`
	FullName string `json:"full_name"`
	Email    string `json:"email"`
}

// WebhookPR represents pull request info in webhook
type WebhookPR struct {
	ID     int64  `json:"id"`
	Number int64  `json:"number"`
	Title  string `json:"title"`
	Body   string `json:"body"`
	State  string `json:"state"`
	Head   struct {
		Ref string `json:"ref"`
		SHA string `json:"sha"`
	} `json:"head"`
	Base struct {
		Ref string `json:"ref"`
		SHA string `json:"sha"`
	} `json:"base"`
	Merged    bool      `json:"merged"`
	MergedAt  time.Time `json:"merged_at,omitempty"`
}

// WebhookCommit represents commit info in webhook
type WebhookCommit struct {
	ID      string    `json:"id"`
	Message string    `json:"message"`
	URL     string    `json:"url"`
	Author  struct {
		Name  string `json:"name"`
		Email string `json:"email"`
	} `json:"author"`
	Timestamp time.Time `json:"timestamp"`
	Added     []string  `json:"added"`
	Modified  []string  `json:"modified"`
	Removed   []string  `json:"removed"`
}

// WebhookHandler handles Gitea webhook events
type WebhookHandler struct {
	onPush        func(*WebhookEvent) error
	onPullRequest func(*WebhookEvent) error
	onMerge       func(*WebhookEvent) error
}

// NewWebhookHandler creates a new webhook handler
func NewWebhookHandler() *WebhookHandler {
	return &WebhookHandler{}
}

// OnPush registers a handler for push events
func (h *WebhookHandler) OnPush(handler func(*WebhookEvent) error) {
	h.onPush = handler
}

// OnPullRequest registers a handler for pull request events
func (h *WebhookHandler) OnPullRequest(handler func(*WebhookEvent) error) {
	h.onPullRequest = handler
}

// OnMerge registers a handler for merge events
func (h *WebhookHandler) OnMerge(handler func(*WebhookEvent) error) {
	h.onMerge = handler
}

// ServeHTTP handles incoming webhook requests
func (h *WebhookHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Read body
	body, err := io.ReadAll(r.Body)
	if err != nil {
		log.Printf("Failed to read webhook body: %v", err)
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Parse event
	var event WebhookEvent
	if err := json.Unmarshal(body, &event); err != nil {
		log.Printf("Failed to parse webhook: %v", err)
		http.Error(w, "Bad request", http.StatusBadRequest)
		return
	}

	// Get event type from header
	eventType := r.Header.Get("X-Gitea-Event")
	log.Printf("Received webhook: %s - %s", eventType, event.Action)

	// Route event
	var handlerErr error
	switch eventType {
	case "push":
		if h.onPush != nil {
			handlerErr = h.onPush(&event)
		}
	case "pull_request":
		if event.Action == "closed" && event.PullRequest != nil && event.PullRequest.Merged {
			// PR was merged
			if h.onMerge != nil {
				handlerErr = h.onMerge(&event)
			}
		} else if h.onPullRequest != nil {
			handlerErr = h.onPullRequest(&event)
		}
	default:
		log.Printf("Unhandled event type: %s", eventType)
	}

	if handlerErr != nil {
		log.Printf("Handler error: %v", handlerErr)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

// GetChangedFiles extracts changed files from a webhook event
func (e *WebhookEvent) GetChangedFiles() []string {
	files := make(map[string]bool)

	for _, commit := range e.Commits {
		for _, file := range commit.Added {
			files[file] = true
		}
		for _, file := range commit.Modified {
			files[file] = true
		}
		for _, file := range commit.Removed {
			files[file] = true
		}
	}

	result := make([]string, 0, len(files))
	for file := range files {
		result = append(result, file)
	}

	return result
}

// IsDocumentChange checks if the event modified a document
func (e *WebhookEvent) IsDocumentChange() bool {
	for _, file := range e.GetChangedFiles() {
		// Check if file is a document (markdown, TOON, etc.)
		if isDocumentFile(file) {
			return true
		}
	}
	return false
}

// isDocumentFile checks if a file is a document
func isDocumentFile(path string) bool {
	extensions := []string{".md", ".toon", ".yaml", ".yml", ".json"}
	for _, ext := range extensions {
		if len(path) > len(ext) && path[len(path)-len(ext):] == ext {
			return true
		}
	}
	return false
}

// String returns a string representation of the event
func (e *WebhookEvent) String() string {
	if e.PullRequest != nil {
		return fmt.Sprintf("PR #%d: %s (%s -> %s)",
			e.PullRequest.Number,
			e.PullRequest.Title,
			e.PullRequest.Head.Ref,
			e.PullRequest.Base.Ref,
		)
	}
	return fmt.Sprintf("Push to %s by %s (%d commits)",
		e.Ref,
		e.Pusher.Login,
		len(e.Commits),
	)
}
