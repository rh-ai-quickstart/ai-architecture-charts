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

	// ✅ FIX: Add "stdio" so GitHub MCP runs in MCP mode
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
			line, err := p.stdout.ReadBytes('\n')
			if err != nil {
				log.Printf("Error reading from GitHub MCP: %v", err)
				close(req.response)
				continue
			}

			log.Printf("Received from GitHub MCP: %s", string(line[:len(line)-1]))
			req.response <- line[:len(line)-1]
		}
		close(req.response)
	}
}

func (p *MCPProxy) Handle(w http.ResponseWriter, r *http.Request) {
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

func (p *MCPProxy) HandleSSE(w http.ResponseWriter, r *http.Request) {
	log.Printf("SSE connection from %s %s", r.RemoteAddr, r.URL.Path)

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	if r.Method == "POST" {
		var msg json.RawMessage
		if err := json.NewDecoder(r.Body).Decode(&msg); err != nil {
			log.Printf("Failed to decode body: %v", err)
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		log.Printf("Received SSE message: %s", string(msg))

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
				http.Error(w, "Failed to get response", http.StatusInternalServerError)
				return
			}

			log.Printf("Sending SSE response: %s", string(response))

			w.Write([]byte("data: "))
			w.Write(response)
			w.Write([]byte("\n\n"))
			flusher.Flush()
		} else {
			<-req.response
			log.Printf("SSE notification processed")
			w.WriteHeader(http.StatusAccepted)
		}
		return
	}

	if r.Method == "GET" {
		log.Printf("SSE stream opened")
		w.Write([]byte(": connected\n\n"))
		flusher.Flush()
		<-r.Context().Done()
		log.Printf("SSE stream closed")
		return
	}

	http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
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

	http.HandleFunc("/sse", proxy.HandleSSE)
	http.HandleFunc("/", proxy.Handle)

	log.Printf("Listening on port %s", port)
	log.Printf("SSE endpoint: http://localhost:%s/sse", port)
	log.Printf("HTTP endpoint: http://localhost:%s/", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
