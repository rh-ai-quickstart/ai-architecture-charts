package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// TestFormatID tests that formatID correctly converts different ID types to comparable strings
func TestFormatID(t *testing.T) {
	tests := []struct {
		name     string
		id       interface{}
		expected string
	}{
		{"integer as float64", float64(1), "1"},
		{"zero", float64(0), "0"},
		{"large number", float64(12345), "12345"},
		{"string id", "abc-123", `"abc-123"`},
		{"empty string", "", `""`},
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

// TestProcessRequestsSkipsNotifications tests the core fix:
// the proxy should skip notifications and return the actual response
func TestProcessRequestsSkipsNotifications(t *testing.T) {
	stdinReader, stdinWriter := io.Pipe()
	stdoutReader, stdoutWriter := io.Pipe()

	proxy := &MCPProxy{
		stdin:    stdinWriter,
		stdout:   bufio.NewReader(stdoutReader),
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()

	// Simulate MCP server: sends notification first, then response
	go func() {
		scanner := bufio.NewScanner(stdinReader)
		for scanner.Scan() {
			// First send a notification (no ID) - this is what GitHub MCP does
			notification := `{"jsonrpc":"2.0","method":"notifications/test","params":{}}`
			stdoutWriter.Write([]byte(notification + "\n"))

			// Then send the actual response with matching ID
			response := `{"jsonrpc":"2.0","id":42,"result":{"data":"test"}}`
			stdoutWriter.Write([]byte(response + "\n"))
		}
	}()

	// Send a request
	reqMsg := json.RawMessage(`{"jsonrpc":"2.0","id":42,"method":"test"}`)
	req := &request{
		msg:       reqMsg,
		isRequest: true,
		response:  make(chan json.RawMessage, 1),
	}
	proxy.requests <- req

	// Get the response
	resp := <-req.response

	// Verify we got the actual response, not the notification
	var respMsg struct {
		ID     interface{} `json:"id"`
		Result interface{} `json:"result"`
	}
	if err := json.Unmarshal(resp, &respMsg); err != nil {
		t.Fatalf("Failed to unmarshal response: %v", err)
	}

	if respMsg.ID == nil {
		t.Error("Expected response with ID, got notification")
	}

	if formatID(respMsg.ID) != formatID(float64(42)) {
		t.Errorf("Expected ID 42, got %v", respMsg.ID)
	}
}

// TestProcessRequestsHandlesMultipleNotifications tests that multiple notifications are skipped
func TestProcessRequestsHandlesMultipleNotifications(t *testing.T) {
	stdinReader, stdinWriter := io.Pipe()
	stdoutReader, stdoutWriter := io.Pipe()

	proxy := &MCPProxy{
		stdin:    stdinWriter,
		stdout:   bufio.NewReader(stdoutReader),
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()

	// Simulate MCP server that sends multiple notifications before response
	go func() {
		scanner := bufio.NewScanner(stdinReader)
		for scanner.Scan() {
			// Send THREE notifications before the response
			notifications := []string{
				`{"jsonrpc":"2.0","method":"notifications/one","params":{}}`,
				`{"jsonrpc":"2.0","method":"notifications/two","params":{}}`,
				`{"jsonrpc":"2.0","method":"notifications/three","params":{}}`,
			}
			for _, n := range notifications {
				stdoutWriter.Write([]byte(n + "\n"))
			}

			// Finally send the response
			response := `{"jsonrpc":"2.0","id":1,"result":{"status":"ok"}}`
			stdoutWriter.Write([]byte(response + "\n"))
		}
	}()

	reqMsg := json.RawMessage(`{"jsonrpc":"2.0","id":1,"method":"test"}`)
	req := &request{
		msg:       reqMsg,
		isRequest: true,
		response:  make(chan json.RawMessage, 1),
	}
	proxy.requests <- req

	resp := <-req.response

	var respMsg MCPMessage
	json.Unmarshal(resp, &respMsg)

	if respMsg.ID == nil {
		t.Error("Expected response with ID, got notification")
	}
}

// TestHTTPHandler tests the HTTP endpoint integration
func TestHTTPHandler(t *testing.T) {
	stdinReader, stdinWriter := io.Pipe()
	stdoutReader, stdoutWriter := io.Pipe()

	proxy := &MCPProxy{
		stdin:    stdinWriter,
		stdout:   bufio.NewReader(stdoutReader),
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()

	// Mock MCP server
	go func() {
		scanner := bufio.NewScanner(stdinReader)
		for scanner.Scan() {
			response := `{"jsonrpc":"2.0","id":0,"result":{"capabilities":{}}}`
			stdoutWriter.Write([]byte(response + "\n"))
		}
	}()

	body := bytes.NewBufferString(`{"jsonrpc":"2.0","id":0,"method":"initialize","params":{}}`)
	req := httptest.NewRequest(http.MethodPost, "/", body)
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	proxy.Handle(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rr.Code)
	}

	if ct := rr.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Expected Content-Type application/json, got %s", ct)
	}

	// Verify response has an ID (not a notification)
	var respMsg MCPMessage
	if err := json.Unmarshal(rr.Body.Bytes(), &respMsg); err != nil {
		t.Fatalf("Response is not valid JSON: %v", err)
	}

	if respMsg.ID == nil {
		t.Error("Response should have an ID")
	}
}

// TestHTTPHandlerNotification tests handling of notifications (no ID)
func TestHTTPHandlerNotification(t *testing.T) {
	stdinReader, stdinWriter := io.Pipe()
	stdoutReader, _ := io.Pipe()

	proxy := &MCPProxy{
		stdin:    stdinWriter,
		stdout:   bufio.NewReader(stdoutReader),
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()

	// Consume stdin (notifications don't expect responses)
	go func() {
		scanner := bufio.NewScanner(stdinReader)
		for scanner.Scan() {
			// Just consume, don't respond
		}
	}()

	body := bytes.NewBufferString(`{"jsonrpc":"2.0","method":"notifications/test","params":{}}`)
	req := httptest.NewRequest(http.MethodPost, "/", body)
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	proxy.Handle(rr, req)

	// Notifications should return 202 Accepted
	if rr.Code != http.StatusAccepted {
		t.Errorf("Expected status 202 for notification, got %d", rr.Code)
	}
}
