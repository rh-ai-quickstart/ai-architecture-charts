package main

import (
	"bufio"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
)

type MCPProxy struct {
	cmd      *exec.Cmd
	stdin    io.WriteCloser
	stdout   *bufio.Reader
	requests chan *request
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
	// The github-mcp-server binary is at /server/github-mcp-server in the official image
	mcpPath := os.Getenv("GITHUB_MCP_PATH")
	if mcpPath == "" {
		mcpPath = "/server/github-mcp-server"
	}

	log.Printf("Starting GitHub MCP Server at: %s", mcpPath)

	cmd := exec.Command(mcpPath, "stdio")

	cmd.Env = append(os.Environ())

	stdin, _ := cmd.StdinPipe()
	stdout, _ := cmd.StdoutPipe()
	stderr, _ := cmd.StderrPipe()

	go func() {
		scanner := bufio.NewScanner(stderr)
		for scanner.Scan() {
			log.Printf("[github-mcp stderr] %s", scanner.Text())
		}
	}()

	if err := cmd.Start(); err != nil {
		return nil, err
	}

	log.Printf("Started GitHub MCP (PID: %d)", cmd.Process.Pid)

	proxy := &MCPProxy{
		cmd:      cmd,
		stdin:    stdin,
		stdout:   bufio.NewReader(stdout),
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()
	return proxy, nil
}

func (p *MCPProxy) processRequests() {
	for req := range p.requests {
		log.Printf("Sending to GitHub MCP: %s", string(req.msg))

		// Write to stdio (newline-delimited JSON)
		p.stdin.Write(append(req.msg, '\n'))

		// Only read response if this is a request (has ID), not a notification
		if req.isRequest {
			// Parse the request to get its ID
			var reqMsg MCPMessage
			json.Unmarshal(req.msg, &reqMsg)
			requestID := reqMsg.ID

			// Keep reading until we get a response matching our request ID
			// (skip any notifications that come before the response)
			for {
				line, err := p.stdout.ReadBytes('\n')
				if err != nil {
					log.Printf("Error reading from GitHub MCP: %v", err)
					close(req.response)
					break
				}

				responseData := line[:len(line)-1]
				log.Printf("Received from GitHub MCP: %s", string(responseData))

				// Parse the response to check if it has an ID
				var respMsg MCPMessage
				json.Unmarshal(responseData, &respMsg)

				// If this is a notification (no ID), log it and continue reading
				if respMsg.ID == nil {
					log.Printf("Received notification (ignoring while waiting for response): %s", string(responseData))
					continue
				}

				// Check if response ID matches request ID
				if respMsg.ID == requestID || (respMsg.ID != nil && requestID != nil && formatID(respMsg.ID) == formatID(requestID)) {
					req.response <- responseData
					break
				}

				// Mismatched ID - this shouldn't happen in normal operation
				log.Printf("Warning: received response with unexpected ID %v (expected %v)", respMsg.ID, requestID)
				req.response <- responseData
				break
			}
		}
		close(req.response)
	}
}

// formatID converts an interface{} ID to a comparable string
func formatID(id interface{}) string {
	// JSON numbers are decoded as float64
	data, _ := json.Marshal(id)
	return string(data)
}

func (p *MCPProxy) Handle(w http.ResponseWriter, r *http.Request) {
	// Handle CORS preflight
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	log.Printf("HTTP request from %s %s", r.RemoteAddr, r.URL.Path)

	var msg json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&msg); err != nil {
		log.Printf("Failed to decode HTTP body: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Printf("Received HTTP request: %s", string(msg))

	var mcpMsg MCPMessage
	json.Unmarshal(msg, &mcpMsg)
	isRequest := mcpMsg.ID != nil

	req := &request{
		msg:       msg,
		isRequest: isRequest,
		response:  make(chan json.RawMessage, 1),
	}
	p.requests <- req

	if isRequest {
		response, ok := <-req.response
		if !ok {
			log.Printf("Failed to get response from GitHub MCP")
			http.Error(w, "Failed to get response", http.StatusInternalServerError)
			return
		}

		log.Printf("Sending HTTP response: %s", string(response))

		w.Header().Set("Content-Type", "application/json")
		w.Write(response)
	} else {
		<-req.response
		log.Printf("Notification processed")
		w.WriteHeader(http.StatusAccepted)
	}
}

// HandleSSEDeprecated returns a friendly message that SSE is deprecated
func HandleSSEDeprecated(w http.ResponseWriter, r *http.Request) {
	log.Printf("SSE request from %s - returning deprecation notice", r.RemoteAddr)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusGone)
	w.Write([]byte(`{"jsonrpc":"2.0","error":{"code":-32000,"message":"SSE transport is deprecated. Please use Streamable HTTP transport instead. Send JSON-RPC requests via POST to the root endpoint (/)."}}`))
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("MCP Streamable HTTP Proxy for GitHub starting...")

	proxy, err := NewMCPProxy()
	if err != nil {
		log.Fatalf("Failed to create proxy: %v", err)
	}

	http.HandleFunc("/sse", HandleSSEDeprecated)
	http.HandleFunc("/", proxy.Handle)

	log.Printf("Listening on port %s", port)
	log.Printf("HTTP endpoint: http://localhost:%s/", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
