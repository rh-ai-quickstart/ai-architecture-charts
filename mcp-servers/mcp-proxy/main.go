// MCP HTTP Proxy - Wraps stdio-based MCP servers and exposes them via streamable HTTP transport
//
// Environment Variables:
//
//	MCP_COMMAND      - Command to run (required, e.g., "/opt/oracle/sqlcl/bin/sql")
//	MCP_ARGS         - Arguments to pass (comma-separated, e.g., "-mcp" or "stdio")
//	MCP_SERVER_NAME  - Name for logging (default: "mcp-server")
//	PORT             - HTTP port to listen on (default: "8080")
//	ENABLE_CORS      - Enable CORS headers (set to "true" or "1")
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strings"
)

type MCPProxy struct {
	serverName string
	cmd        *exec.Cmd
	stdin      io.WriteCloser
	stdout     *bufio.Reader
	requests   chan *request
	enableCORS bool
}

type request struct {
	msg       json.RawMessage
	isRequest bool
	response  chan json.RawMessage
}

type MCPMessage struct {
	ID interface{} `json:"id,omitempty"`
}

func NewMCPProxy() (*MCPProxy, error) {
	// Get configuration from environment
	command := os.Getenv("MCP_COMMAND")
	if command == "" {
		return nil, fmt.Errorf("MCP_COMMAND environment variable is required")
	}

	serverName := os.Getenv("MCP_SERVER_NAME")
	if serverName == "" {
		serverName = "mcp-server"
	}

	enableCORS := os.Getenv("ENABLE_CORS") == "true" || os.Getenv("ENABLE_CORS") == "1"

	// Parse arguments (comma-separated)
	var args []string
	if argsStr := os.Getenv("MCP_ARGS"); argsStr != "" {
		args = strings.Split(argsStr, ",")
		// Trim whitespace from each arg
		for i, arg := range args {
			args[i] = strings.TrimSpace(arg)
		}
	}

	log.Printf("[%s] Starting MCP server: %s %v", serverName, command, args)

	cmd := exec.Command(command, args...)
	cmd.Env = os.Environ()

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to get stdin pipe: %w", err)
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to get stdout pipe: %w", err)
	}

	stderr, err := cmd.StderrPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to get stderr pipe: %w", err)
	}

	// Log stderr from the MCP server
	go func() {
		scanner := bufio.NewScanner(stderr)
		for scanner.Scan() {
			log.Printf("[%s stderr] %s", serverName, scanner.Text())
		}
	}()

	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start MCP server: %w", err)
	}

	log.Printf("[%s] Started MCP server (PID: %d)", serverName, cmd.Process.Pid)

	proxy := &MCPProxy{
		serverName: serverName,
		cmd:        cmd,
		stdin:      stdin,
		stdout:     bufio.NewReader(stdout),
		requests:   make(chan *request, 100),
		enableCORS: enableCORS,
	}

	go proxy.processRequests()
	return proxy, nil
}

func (p *MCPProxy) processRequests() {
	for req := range p.requests {
		log.Printf("[%s] Sending: %s", p.serverName, string(req.msg))

		// Write to stdio (newline-delimited JSON)
		if _, err := p.stdin.Write(append(req.msg, '\n')); err != nil {
			log.Printf("[%s] Error writing to stdin: %v", p.serverName, err)
			close(req.response)
			continue
		}

		// Only read response if this is a request (has ID), not a notification
		if req.isRequest {
			response, err := p.readResponse()
			if err != nil {
				log.Printf("[%s] Error reading response: %v", p.serverName, err)
				close(req.response)
				continue
			}
			req.response <- response
		}
		close(req.response)
	}
}

func (p *MCPProxy) readResponse() (json.RawMessage, error) {
	for {
		line, err := p.stdout.ReadBytes('\n')
		if err != nil {
			return nil, fmt.Errorf("error reading from MCP server: %w", err)
		}

		responseData := line[:len(line)-1]
		log.Printf("[%s] Received: %s", p.serverName, string(responseData))

		// Parse the response to check if it has an ID
		var respMsg MCPMessage
		json.Unmarshal(responseData, &respMsg)

		// Skip notifications (messages without ID)
		if respMsg.ID == nil {
			log.Printf("[%s] Skipping notification", p.serverName)
			continue
		}

		return responseData, nil
	}
}

func (p *MCPProxy) Handle(w http.ResponseWriter, r *http.Request) {
	// Handle CORS if enabled
	if p.enableCORS {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
	}

	log.Printf("[%s] HTTP request from %s %s", p.serverName, r.RemoteAddr, r.URL.Path)

	// Read HTTP JSON body
	var msg json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&msg); err != nil {
		log.Printf("[%s] Failed to decode HTTP body: %v", p.serverName, err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Printf("[%s] Received: %s", p.serverName, string(msg))

	// Check if this is a request (has ID) or notification (no ID)
	var mcpMsg MCPMessage
	json.Unmarshal(msg, &mcpMsg)
	isRequest := mcpMsg.ID != nil

	// Send request to MCP server
	req := &request{
		msg:       msg,
		isRequest: isRequest,
		response:  make(chan json.RawMessage, 1),
	}
	p.requests <- req

	// Wait for response (only if it's a request)
	if isRequest {
		response, ok := <-req.response
		if !ok {
			log.Printf("[%s] Failed to get response", p.serverName)
			http.Error(w, "Failed to get response", http.StatusInternalServerError)
			return
		}

		log.Printf("[%s] Responding: %s", p.serverName, string(response))

		w.Header().Set("Content-Type", "application/json")
		w.Write(response)
	} else {
		// For notifications, wait for processing and return 202 Accepted
		<-req.response
		log.Printf("[%s] Notification processed", p.serverName)
		w.WriteHeader(http.StatusAccepted)
	}
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	serverName := os.Getenv("MCP_SERVER_NAME")
	if serverName == "" {
		serverName = "mcp-proxy"
	}

	log.Printf("[%s] MCP HTTP Proxy starting...", serverName)

	proxy, err := NewMCPProxy()
	if err != nil {
		log.Fatalf("Failed to create proxy: %v", err)
	}

	http.HandleFunc("/", proxy.Handle)
	log.Printf("[%s] Listening on port %s", serverName, port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
