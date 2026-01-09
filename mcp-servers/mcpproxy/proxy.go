// Package mcpproxy provides a reusable HTTP proxy for MCP (Model Context Protocol) servers.
// It wraps stdio-based MCP servers and exposes them via streamable HTTP transport.
package mcpproxy

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"

	"github.com/creack/pty"
	"golang.org/x/term"
)

// Config defines the configuration for an MCP proxy server.
type Config struct {
	// ServerName is used for logging (e.g., "github-mcp", "sqlcl")
	ServerName string

	// CommandPath is the default path to the MCP server binary
	CommandPath string

	// CommandArgs are the arguments to pass to the MCP server (e.g., "stdio", "-mcp")
	CommandArgs []string

	// PathEnvVar is the environment variable name to override CommandPath (optional)
	PathEnvVar string

	// Port is the HTTP port to listen on (default: "8080")
	Port string

	// EnableCORS adds CORS headers to responses
	EnableCORS bool

	// UsePTY runs the MCP server in a pseudo-terminal to force line buffering.
	// Enable this for MCP servers that buffer stdout (e.g., Java-based servers like SQLcl).
	UsePTY bool

	// SkipNotifications enables strict response ID matching when waiting for a response.
	// When true: waits for a response with an ID matching the request ID (skipping mismatches)
	// When false: returns the first response with any ID (suitable for sequential request/response)
	// Note: Notifications (messages without ID) are always skipped regardless of this setting.
	SkipNotifications bool

	// ResponseMiddleware is called on each response before sending to client (optional)
	// Use this for server-specific response processing (e.g., error detection)
	ResponseMiddleware func([]byte) []byte

	// RequestMiddleware is called on each request before sending to MCP server (optional)
	RequestMiddleware func([]byte) []byte

	// ExtraRoutes are additional HTTP routes to register (optional)
	// Use this for things like deprecation notices on old endpoints
	ExtraRoutes map[string]http.HandlerFunc
}

// MCPProxy handles the communication between HTTP clients and stdio-based MCP servers.
type MCPProxy struct {
	config   Config
	cmd      *exec.Cmd
	stdin    io.WriteCloser
	stdout   *bufio.Reader
	ptyFile  *os.File // PTY master file (if UsePTY is enabled)
	requests chan *request
}

type request struct {
	msg       json.RawMessage
	isRequest bool
	response  chan json.RawMessage
}

// MCPMessage is used to extract the ID from MCP messages.
type MCPMessage struct {
	ID interface{} `json:"id,omitempty"`
}

// NewMCPProxy creates a new MCP proxy with the given configuration.
func NewMCPProxy(cfg Config) (*MCPProxy, error) {
	// Apply defaults
	if cfg.Port == "" {
		cfg.Port = "8080"
	}

	// Check for path override from environment
	cmdPath := cfg.CommandPath
	if cfg.PathEnvVar != "" {
		if envPath := os.Getenv(cfg.PathEnvVar); envPath != "" {
			cmdPath = envPath
		}
	}

	log.Printf("[%s] Starting MCP server at: %s (PTY: %v)", cfg.ServerName, cmdPath, cfg.UsePTY)

	cmd := exec.Command(cmdPath, cfg.CommandArgs...)
	cmd.Env = append(os.Environ())

	var stdin io.WriteCloser
	var stdout io.Reader
	var ptyFile *os.File

	if cfg.UsePTY {
		// Use PTY for stdin/stdout to force line buffering
		var err error
		ptyFile, err = pty.Start(cmd)
		if err != nil {
			return nil, fmt.Errorf("failed to start PTY: %w", err)
		}

		// Disable echo on PTY to prevent input from being echoed back
		oldState, err := term.MakeRaw(int(ptyFile.Fd()))
		if err != nil {
			log.Printf("[%s] Warning: could not set raw mode on PTY: %v", cfg.ServerName, err)
		} else {
			// We don't restore the state since we want raw mode for the lifetime of the proxy
			_ = oldState
		}

		// PTY master is used for both reading and writing
		stdin = ptyFile
		stdout = ptyFile

		log.Printf("[%s] Started MCP server with PTY (PID: %d)", cfg.ServerName, cmd.Process.Pid)
	} else {
		// Use regular pipes
		var err error
		stdin, err = cmd.StdinPipe()
		if err != nil {
			return nil, fmt.Errorf("failed to get stdin pipe: %w", err)
		}

		stdout, err = cmd.StdoutPipe()
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
				log.Printf("[%s stderr] %s", cfg.ServerName, scanner.Text())
			}
		}()

		if err := cmd.Start(); err != nil {
			return nil, fmt.Errorf("failed to start MCP server: %w", err)
		}

		log.Printf("[%s] Started MCP server (PID: %d)", cfg.ServerName, cmd.Process.Pid)
	}

	proxy := &MCPProxy{
		config:   cfg,
		cmd:      cmd,
		stdin:    stdin,
		stdout:   bufio.NewReader(stdout),
		ptyFile:  ptyFile,
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()
	return proxy, nil
}

func (p *MCPProxy) processRequests() {
	for req := range p.requests {
		msg := req.msg

		// Apply request middleware if configured
		if p.config.RequestMiddleware != nil {
			msg = p.config.RequestMiddleware(msg)
		}

		log.Printf("[%s] Sending: %s", p.config.ServerName, string(msg))

		// Write to stdio (newline-delimited JSON)
		if _, err := p.stdin.Write(append(msg, '\n')); err != nil {
			log.Printf("[%s] Error writing to stdin: %v", p.config.ServerName, err)
			close(req.response)
			continue
		}

		// Only read response if this is a request (has ID), not a notification
		if req.isRequest {
			// Use the potentially middleware-modified msg for ID matching
			response, err := p.readResponse(msg)
			if err != nil {
				log.Printf("[%s] Error reading response: %v", p.config.ServerName, err)
				close(req.response)
				continue
			}

			// Apply response middleware if configured
			if p.config.ResponseMiddleware != nil {
				response = p.config.ResponseMiddleware(response)
			}

			req.response <- response
		}
		close(req.response)
	}
}

func (p *MCPProxy) readResponse(originalRequest json.RawMessage) (json.RawMessage, error) {
	// Parse the request to get its ID for matching
	var reqMsg MCPMessage
	json.Unmarshal(originalRequest, &reqMsg)
	requestID := reqMsg.ID

	for {
		line, err := p.stdout.ReadBytes('\n')
		if err != nil {
			return nil, fmt.Errorf("error reading from MCP server: %w", err)
		}

		// Remove trailing newline and carriage return (PTY may add \r\n)
		responseData := line
		for len(responseData) > 0 && (responseData[len(responseData)-1] == '\n' || responseData[len(responseData)-1] == '\r') {
			responseData = responseData[:len(responseData)-1]
		}

		// Skip empty lines
		if len(responseData) == 0 {
			continue
		}

		// Skip lines that don't look like JSON (e.g., PTY control sequences, log messages)
		if responseData[0] != '{' {
			log.Printf("[%s] Skipping non-JSON line: %s", p.config.ServerName, string(responseData))
			continue
		}

		log.Printf("[%s] Received: %s", p.config.ServerName, string(responseData))

		// Parse the response to check if it has an ID
		var respMsg MCPMessage
		json.Unmarshal(responseData, &respMsg)

		// Always skip notifications (messages without ID)
		// Notifications are server-initiated messages that don't correspond to any request
		if respMsg.ID == nil {
			log.Printf("[%s] Skipping notification while waiting for response", p.config.ServerName)
			continue
		}

		// If SkipNotifications is disabled, return the first response with an ID
		// This is suitable for MCP servers that don't emit notifications between request/response
		if !p.config.SkipNotifications {
			return responseData, nil
		}

		// When SkipNotifications is enabled, also verify the response ID matches the request ID
		// This handles servers that may send multiple responses or out-of-order responses
		if respMsg.ID == requestID || formatID(respMsg.ID) == formatID(requestID) {
			return responseData, nil
		}

		// Mismatched ID - log warning and return anyway to prevent hanging
		log.Printf("[%s] Warning: received response with unexpected ID %v (expected %v)",
			p.config.ServerName, respMsg.ID, requestID)
		return responseData, nil
	}
}

// formatID converts an interface{} ID to a comparable string.
func formatID(id interface{}) string {
	if id == nil {
		return ""
	}
	data, _ := json.Marshal(id)
	return string(data)
}

// Handle is the HTTP handler for MCP requests.
func (p *MCPProxy) Handle(w http.ResponseWriter, r *http.Request) {
	// Handle CORS if enabled
	if p.config.EnableCORS {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}
	}

	log.Printf("[%s] HTTP request from %s %s", p.config.ServerName, r.RemoteAddr, r.URL.Path)

	// Read HTTP JSON body
	var msg json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&msg); err != nil {
		log.Printf("[%s] Failed to decode HTTP body: %v", p.config.ServerName, err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Printf("[%s] Received HTTP request: %s", p.config.ServerName, string(msg))

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
			log.Printf("[%s] Failed to get response from MCP server", p.config.ServerName)
			http.Error(w, "Failed to get response", http.StatusInternalServerError)
			return
		}

		log.Printf("[%s] Sending HTTP response: %s", p.config.ServerName, string(response))

		w.Header().Set("Content-Type", "application/json")
		w.Write(response)
	} else {
		// For notifications, wait for processing to complete and return 202 Accepted
		<-req.response
		log.Printf("[%s] Notification processed", p.config.ServerName)
		w.WriteHeader(http.StatusAccepted)
	}
}

// Run starts the MCP proxy server with the given configuration.
// This is a convenience function that creates the proxy and starts the HTTP server.
func Run(cfg Config) error {
	if cfg.Port == "" {
		cfg.Port = "8080"
	}

	log.Printf("[%s] MCP Streamable HTTP Proxy starting...", cfg.ServerName)

	proxy, err := NewMCPProxy(cfg)
	if err != nil {
		return fmt.Errorf("failed to create proxy: %w", err)
	}

	// Register extra routes first (so they take precedence over the catch-all)
	for path, handler := range cfg.ExtraRoutes {
		log.Printf("[%s] Registering extra route: %s", cfg.ServerName, path)
		http.HandleFunc(path, handler)
	}

	// Register the main handler
	http.HandleFunc("/", proxy.Handle)

	log.Printf("[%s] Listening on port %s", cfg.ServerName, cfg.Port)
	log.Printf("[%s] HTTP endpoint: http://localhost:%s/", cfg.ServerName, cfg.Port)

	return http.ListenAndServe(":"+cfg.Port, nil)
}
