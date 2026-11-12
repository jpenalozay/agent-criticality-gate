// Package gitea provides Gitea client for Git-based document management
package gitea

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

// Client is a Gitea API client
type Client struct {
	baseURL    string
	token      string
	httpClient *http.Client
}

// New creates a new Gitea client
func New(baseURL, token string) *Client {
	return &Client{
		baseURL: baseURL,
		token:   token,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// Repository represents a Gitea repository
type Repository struct {
	ID          int64  `json:"id"`
	Name        string `json:"name"`
	FullName    string `json:"full_name"`
	Description string `json:"description"`
	Private     bool   `json:"private"`
	DefaultBranch string `json:"default_branch"`
}

// FileContent represents a file in a repository
type FileContent struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	SHA         string `json:"sha"`
	Size        int64  `json:"size"`
	Content     string `json:"content"` // Base64 encoded
	Encoding    string `json:"encoding"`
	DownloadURL string `json:"download_url"`
}

// CreateRepoRequest represents a repository creation request
type CreateRepoRequest struct {
	Name          string `json:"name"`
	Description   string `json:"description"`
	Private       bool   `json:"private"`
	AutoInit      bool   `json:"auto_init"`
	DefaultBranch string `json:"default_branch"`
}

// CreateFileRequest represents a file creation request
type CreateFileRequest struct {
	Content string `json:"content"` // Base64 encoded
	Message string `json:"message"`
	Branch  string `json:"branch,omitempty"`
}

// UpdateFileRequest represents a file update request
type UpdateFileRequest struct {
	Content string `json:"content"` // Base64 encoded
	Message string `json:"message"`
	SHA     string `json:"sha"`
	Branch  string `json:"branch,omitempty"`
}

// PullRequest represents a pull request
type PullRequest struct {
	ID     int64  `json:"id"`
	Number int64  `json:"number"`
	Title  string `json:"title"`
	Body   string `json:"body"`
	State  string `json:"state"`
	Head   struct {
		Ref string `json:"ref"`
	} `json:"head"`
	Base struct {
		Ref string `json:"ref"`
	} `json:"base"`
}

// CreatePRRequest represents a pull request creation request
type CreatePRRequest struct {
	Title string `json:"title"`
	Body  string `json:"body"`
	Head  string `json:"head"`
	Base  string `json:"base"`
}

// Webhook represents a webhook configuration
type Webhook struct {
	ID     int64  `json:"id"`
	Type   string `json:"type"`
	URL    string `json:"config.url"`
	Active bool   `json:"active"`
}

// CreateWebhookRequest represents a webhook creation request
type CreateWebhookRequest struct {
	Type   string                 `json:"type"`
	Config map[string]interface{} `json:"config"`
	Events []string               `json:"events"`
	Active bool                   `json:"active"`
}

// doRequest performs an HTTP request
func (c *Client) doRequest(ctx context.Context, method, path string, body interface{}) (*http.Response, error) {
	var bodyReader io.Reader
	if body != nil {
		jsonData, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal body: %w", err)
		}
		bodyReader = bytes.NewReader(jsonData)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "token "+c.token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}

	return resp, nil
}

// CreateRepository creates a new repository
func (c *Client) CreateRepository(ctx context.Context, owner string, req *CreateRepoRequest) (*Repository, error) {
	resp, err := c.doRequest(ctx, "POST", fmt.Sprintf("/api/v1/orgs/%s/repos", owner), req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("failed to create repository: %s - %s", resp.Status, string(body))
	}

	var repo Repository
	if err := json.NewDecoder(resp.Body).Decode(&repo); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	log.Printf("Created repository: %s", repo.FullName)
	return &repo, nil
}

// GetFile retrieves a file from a repository
func (c *Client) GetFile(ctx context.Context, owner, repo, branch, path string) (*FileContent, error) {
	url := fmt.Sprintf("/api/v1/repos/%s/%s/contents/%s?ref=%s", owner, repo, path, branch)
	resp, err := c.doRequest(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("file not found: %s", path)
	}

	var file FileContent
	if err := json.NewDecoder(resp.Body).Decode(&file); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &file, nil
}

// CreateFile creates a new file in a repository
func (c *Client) CreateFile(ctx context.Context, owner, repo, path string, req *CreateFileRequest) error {
	url := fmt.Sprintf("/api/v1/repos/%s/%s/contents/%s", owner, repo, path)
	resp, err := c.doRequest(ctx, "POST", url, req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to create file: %s - %s", resp.Status, string(body))
	}

	log.Printf("Created file: %s/%s/%s", owner, repo, path)
	return nil
}

// UpdateFile updates an existing file in a repository
func (c *Client) UpdateFile(ctx context.Context, owner, repo, path string, req *UpdateFileRequest) error {
	url := fmt.Sprintf("/api/v1/repos/%s/%s/contents/%s", owner, repo, path)
	resp, err := c.doRequest(ctx, "PUT", url, req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to update file: %s - %s", resp.Status, string(body))
	}

	log.Printf("Updated file: %s/%s/%s", owner, repo, path)
	return nil
}

// CreatePullRequest creates a new pull request
func (c *Client) CreatePullRequest(ctx context.Context, owner, repo string, req *CreatePRRequest) (*PullRequest, error) {
	url := fmt.Sprintf("/api/v1/repos/%s/%s/pulls", owner, repo)
	resp, err := c.doRequest(ctx, "POST", url, req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("failed to create PR: %s - %s", resp.Status, string(body))
	}

	var pr PullRequest
	if err := json.NewDecoder(resp.Body).Decode(&pr); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	log.Printf("Created PR #%d: %s", pr.Number, pr.Title)
	return &pr, nil
}

// MergePullRequest merges a pull request
func (c *Client) MergePullRequest(ctx context.Context, owner, repo string, prNumber int64) error {
	url := fmt.Sprintf("/api/v1/repos/%s/%s/pulls/%d/merge", owner, repo, prNumber)
	resp, err := c.doRequest(ctx, "POST", url, map[string]string{
		"Do": "merge",
	})
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to merge PR: %s - %s", resp.Status, string(body))
	}

	log.Printf("Merged PR #%d", prNumber)
	return nil
}

// CreateWebhook creates a webhook for a repository
func (c *Client) CreateWebhook(ctx context.Context, owner, repo string, webhookURL string, events []string) error {
	req := &CreateWebhookRequest{
		Type: "gitea",
		Config: map[string]interface{}{
			"url":          webhookURL,
			"content_type": "json",
		},
		Events: events,
		Active: true,
	}

	url := fmt.Sprintf("/api/v1/repos/%s/%s/hooks", owner, repo)
	resp, err := c.doRequest(ctx, "POST", url, req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("failed to create webhook: %s - %s", resp.Status, string(body))
	}

	log.Printf("Created webhook for %s/%s -> %s", owner, repo, webhookURL)
	return nil
}

// DecodeContent decodes base64-encoded file content
func DecodeContent(encoded string) ([]byte, error) {
	return base64.StdEncoding.DecodeString(encoded)
}

// EncodeContent encodes content to base64
func EncodeContent(data []byte) string {
	return base64.StdEncoding.EncodeToString(data)
}
