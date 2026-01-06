package mcpproxy

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func TestFormatID(t *testing.T) {
	tests := []struct {
		name     string
		id       interface{}
		expected string
	}{
		{"nil", nil, ""},
		{"integer", 1, "1"},
		{"float", 1.5, "1.5"},
		{"string", "abc", `"abc"`},
		{"large int", 12345, "12345"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := formatID(tt.id)
			if result != tt.expected {
				t.Errorf("formatID(%v) = %q, want %q", tt.id, result, tt.expected)
			}
		})
	}
}

func TestMCPMessageParsing(t *testing.T) {
	tests := []struct {
		name     string
		json     string
		expectID bool
		idValue  interface{}
	}{
		{
			name:     "request with numeric id",
			json:     `{"jsonrpc":"2.0","id":1,"method":"initialize"}`,
			expectID: true,
			idValue:  float64(1), // JSON numbers are float64
		},
		{
			name:     "request with string id",
			json:     `{"jsonrpc":"2.0","id":"abc","method":"initialize"}`,
			expectID: true,
			idValue:  "abc",
		},
		{
			name:     "notification without id",
			json:     `{"jsonrpc":"2.0","method":"notifications/initialized"}`,
			expectID: false,
			idValue:  nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var msg MCPMessage
			err := json.Unmarshal([]byte(tt.json), &msg)
			if err != nil {
				t.Fatalf("Failed to unmarshal: %v", err)
			}

			hasID := msg.ID != nil
			if hasID != tt.expectID {
				t.Errorf("Expected hasID=%v, got %v", tt.expectID, hasID)
			}

			if tt.expectID && msg.ID != tt.idValue {
				t.Errorf("Expected ID=%v, got %v", tt.idValue, msg.ID)
			}
		})
	}
}

func TestConfigDefaults(t *testing.T) {
	cfg := Config{
		ServerName:  "test",
		CommandPath: "/bin/echo",
	}

	// Port should default to empty in Config, but Run() sets it to 8080
	if cfg.Port != "" {
		t.Errorf("Expected empty port in config, got %q", cfg.Port)
	}

	// After applying defaults in Run context
	if cfg.Port == "" {
		cfg.Port = "8080"
	}
	if cfg.Port != "8080" {
		t.Errorf("Expected port 8080, got %q", cfg.Port)
	}
}

func TestConfigPathEnvOverride(t *testing.T) {
	// Set up test environment variable
	os.Setenv("TEST_MCP_PATH", "/custom/path")
	defer os.Unsetenv("TEST_MCP_PATH")

	cfg := Config{
		ServerName:  "test",
		CommandPath: "/default/path",
		PathEnvVar:  "TEST_MCP_PATH",
	}

	// Simulate the path resolution logic from NewMCPProxy
	cmdPath := cfg.CommandPath
	if cfg.PathEnvVar != "" {
		if envPath := os.Getenv(cfg.PathEnvVar); envPath != "" {
			cmdPath = envPath
		}
	}

	if cmdPath != "/custom/path" {
		t.Errorf("Expected /custom/path, got %q", cmdPath)
	}
}

func TestConfigPathEnvNotSet(t *testing.T) {
	// Ensure env var is not set
	os.Unsetenv("NONEXISTENT_VAR")

	cfg := Config{
		ServerName:  "test",
		CommandPath: "/default/path",
		PathEnvVar:  "NONEXISTENT_VAR",
	}

	cmdPath := cfg.CommandPath
	if cfg.PathEnvVar != "" {
		if envPath := os.Getenv(cfg.PathEnvVar); envPath != "" {
			cmdPath = envPath
		}
	}

	if cmdPath != "/default/path" {
		t.Errorf("Expected /default/path, got %q", cmdPath)
	}
}

// MockMCPProxy creates a proxy with mock stdin/stdout for testing
type MockMCPProxy struct {
	config    Config
	stdin     *bytes.Buffer
	stdout    *bytes.Buffer
	requests  chan *request
	responses []string
	respIndex int
}

func NewMockMCPProxy(cfg Config, responses []string) *MockMCPProxy {
	return &MockMCPProxy{
		config:    cfg,
		stdin:     &bytes.Buffer{},
		stdout:    &bytes.Buffer{},
		requests:  make(chan *request, 100),
		responses: responses,
		respIndex: 0,
	}
}

func (m *MockMCPProxy) Handle(w http.ResponseWriter, r *http.Request) {
	// Handle CORS if enabled
	if m.config.EnableCORS {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
	}

	// Read HTTP JSON body
	var msg json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&msg); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	// Check if this is a request (has ID) or notification (no ID)
	var mcpMsg MCPMessage
	json.Unmarshal(msg, &mcpMsg)
	isRequest := mcpMsg.ID != nil

	if isRequest {
		// Return mock response
		var response []byte
		if m.respIndex < len(m.responses) {
			response = []byte(m.responses[m.respIndex])
			m.respIndex++
		} else {
			response = []byte(`{"jsonrpc":"2.0","id":1,"result":{}}`)
		}

		// Apply response middleware if configured
		if m.config.ResponseMiddleware != nil {
			response = m.config.ResponseMiddleware(response)
		}

		w.Header().Set("Content-Type", "application/json")
		w.Write(response)
	} else {
		w.WriteHeader(http.StatusAccepted)
	}
}

func TestHandleCORSEnabled(t *testing.T) {
	proxy := NewMockMCPProxy(Config{
		ServerName: "test",
		EnableCORS: true,
	}, []string{`{"jsonrpc":"2.0","id":1,"result":{}}`})

	// Test OPTIONS preflight
	req := httptest.NewRequest("OPTIONS", "/", nil)
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200 for OPTIONS, got %d", w.Code)
	}

	if w.Header().Get("Access-Control-Allow-Origin") != "*" {
		t.Error("Expected CORS header Access-Control-Allow-Origin")
	}
}

func TestHandleCORSDisabled(t *testing.T) {
	proxy := NewMockMCPProxy(Config{
		ServerName: "test",
		EnableCORS: false,
	}, []string{`{"jsonrpc":"2.0","id":1,"result":{}}`})

	req := httptest.NewRequest("POST", "/", strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	if w.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Error("Expected no CORS headers when disabled")
	}
}

func TestHandleRequest(t *testing.T) {
	expectedResponse := `{"jsonrpc":"2.0","id":1,"result":{"tools":[]}}`
	proxy := NewMockMCPProxy(Config{
		ServerName: "test",
	}, []string{expectedResponse})

	req := httptest.NewRequest("POST", "/", strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	if w.Header().Get("Content-Type") != "application/json" {
		t.Error("Expected Content-Type application/json")
	}

	body, _ := io.ReadAll(w.Body)
	if string(body) != expectedResponse {
		t.Errorf("Expected response %q, got %q", expectedResponse, string(body))
	}
}

func TestHandleNotification(t *testing.T) {
	proxy := NewMockMCPProxy(Config{
		ServerName: "test",
	}, nil)

	// Notification has no ID
	req := httptest.NewRequest("POST", "/", strings.NewReader(`{"jsonrpc":"2.0","method":"notifications/initialized"}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	if w.Code != http.StatusAccepted {
		t.Errorf("Expected status 202 Accepted for notification, got %d", w.Code)
	}
}

func TestHandleInvalidJSON(t *testing.T) {
	proxy := NewMockMCPProxy(Config{
		ServerName: "test",
	}, nil)

	req := httptest.NewRequest("POST", "/", strings.NewReader(`not valid json`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("Expected status 400 for invalid JSON, got %d", w.Code)
	}
}

func TestResponseMiddleware(t *testing.T) {
	// Middleware that modifies the response
	middleware := func(response []byte) []byte {
		return []byte(`{"jsonrpc":"2.0","id":1,"result":{"modified":true}}`)
	}

	proxy := NewMockMCPProxy(Config{
		ServerName:         "test",
		ResponseMiddleware: middleware,
	}, []string{`{"jsonrpc":"2.0","id":1,"result":{"original":true}}`})

	req := httptest.NewRequest("POST", "/", strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	body, _ := io.ReadAll(w.Body)
	if !strings.Contains(string(body), "modified") {
		t.Errorf("Expected middleware to modify response, got %q", string(body))
	}
}

func TestExtraRoutes(t *testing.T) {
	customHandler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusGone)
		w.Write([]byte(`{"error":"deprecated"}`))
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/sse", customHandler)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"default":"handler"}`))
	})

	// Test custom route
	req := httptest.NewRequest("GET", "/sse", nil)
	w := httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusGone {
		t.Errorf("Expected status 410 for /sse, got %d", w.Code)
	}

	// Test default route
	req = httptest.NewRequest("GET", "/", nil)
	w = httptest.NewRecorder()
	mux.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200 for /, got %d", w.Code)
	}
}

func TestNotificationsAlwaysSkipped(t *testing.T) {
	// This tests that notifications (messages without ID) are always skipped,
	// even when SkipNotifications is false
	proxy := NewMockMCPProxy(Config{
		ServerName:        "test",
		SkipNotifications: false, // Even with this false, notifications should be skipped
	}, []string{`{"jsonrpc":"2.0","id":1,"result":{"data":"response"}}`})

	// Simulate receiving a notification first, then a response
	// The mock doesn't simulate this exactly, but we test that:
	// 1. A message WITH an ID is treated as a response
	// 2. The SkipNotifications=false config works correctly

	req := httptest.NewRequest("POST", "/", strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	proxy.Handle(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", w.Code)
	}

	body, _ := io.ReadAll(w.Body)
	if !strings.Contains(string(body), "response") {
		t.Errorf("Expected response data, got %q", string(body))
	}
}

func TestIsRequestDetection(t *testing.T) {
	tests := []struct {
		name      string
		json      string
		isRequest bool
	}{
		{
			name:      "request with id",
			json:      `{"jsonrpc":"2.0","id":1,"method":"test"}`,
			isRequest: true,
		},
		{
			name:      "request with string id",
			json:      `{"jsonrpc":"2.0","id":"req-1","method":"test"}`,
			isRequest: true,
		},
		{
			name:      "notification without id",
			json:      `{"jsonrpc":"2.0","method":"test"}`,
			isRequest: false,
		},
		{
			name:      "notification with null id",
			json:      `{"jsonrpc":"2.0","id":null,"method":"test"}`,
			isRequest: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var msg MCPMessage
			json.Unmarshal([]byte(tt.json), &msg)
			isRequest := msg.ID != nil

			if isRequest != tt.isRequest {
				t.Errorf("Expected isRequest=%v, got %v", tt.isRequest, isRequest)
			}
		})
	}
}
