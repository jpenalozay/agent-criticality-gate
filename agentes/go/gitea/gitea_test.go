package gitea

import (
	"context"
	"testing"
	"time"
)

func TestGiteaClient(t *testing.T) {
	// Skip if Gitea not configured
	baseURL := "http://localhost:3000"
	token := "" // Set this to test

	if token == "" {
		t.Skip("Skipping Gitea tests: no token configured")
	}

	client := New(baseURL, token)
	ctx := context.Background()

	t.Run("CreateRepository", func(t *testing.T) {
		req := &CreateRepoRequest{
			Name:          "test-repo-" + time.Now().Format("20060102150405"),
			Description:   "Test repository",
			Private:       true,
			AutoInit:      true,
			DefaultBranch: "main",
		}

		repo, err := client.CreateRepository(ctx, "framework", req)
		if err != nil {
			t.Fatalf("Failed to create repository: %v", err)
		}

		if repo.Name != req.Name {
			t.Errorf("Expected repo name %s, got %s", req.Name, repo.Name)
		}
	})

	t.Run("CreateAndGetFile", func(t *testing.T) {
		content := []byte("# Test Document\n\nThis is a test.")
		encoded := EncodeContent(content)

		// Create file
		err := client.CreateFile(ctx, "framework", "docs-architecture", "test.md", &CreateFileRequest{
			Content: encoded,
			Message: "Add test file",
			Branch:  "main",
		})
		if err != nil {
			t.Fatalf("Failed to create file: %v", err)
		}

		// Get file
		file, err := client.GetFile(ctx, "framework", "docs-architecture", "main", "test.md")
		if err != nil {
			t.Fatalf("Failed to get file: %v", err)
		}

		// Decode content
		decoded, err := DecodeContent(file.Content)
		if err != nil {
			t.Fatalf("Failed to decode content: %v", err)
		}

		if string(decoded) != string(content) {
			t.Errorf("Content mismatch.\nExpected: %s\nGot: %s", string(content), string(decoded))
		}
	})
}

func TestWebhookEvent(t *testing.T) {
	t.Run("GetChangedFiles", func(t *testing.T) {
		event := &WebhookEvent{
			Commits: []WebhookCommit{
				{
					Added:    []string{"file1.md", "file2.md"},
					Modified: []string{"file3.md"},
					Removed:  []string{"file4.md"},
				},
				{
					Modified: []string{"file3.md", "file5.md"},
				},
			},
		}

		files := event.GetChangedFiles()
		if len(files) != 5 {
			t.Errorf("Expected 5 unique files, got %d", len(files))
		}
	})

	t.Run("IsDocumentChange", func(t *testing.T) {
		event := &WebhookEvent{
			Commits: []WebhookCommit{
				{
					Added: []string{"README.md", "src/main.go"},
				},
			},
		}

		if !event.IsDocumentChange() {
			t.Error("Expected document change to be detected")
		}

		event.Commits[0].Added = []string{"src/main.go"}
		if event.IsDocumentChange() {
			t.Error("Expected no document change")
		}
	})
}
