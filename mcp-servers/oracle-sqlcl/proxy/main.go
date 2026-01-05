package main

import (
	"encoding/json"
	"log"
	"os"
	"regexp"
	"strings"

	"mcpproxy"
)

// Oracle-specific types for error detection
type MCPResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   json.RawMessage `json:"error,omitempty"`
}

type MCPResult struct {
	Content []MCPContent `json:"content,omitempty"`
	IsError bool         `json:"isError,omitempty"`
}

type MCPContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

var errorPattern = regexp.MustCompile(`(?i)(ORA-\d+|SP2-\d+|Error:.*(ORA-\d+|SP2-\d+))`)

// markOracleErrors checks MCP responses for Oracle errors and marks them as isError=true
func markOracleErrors(response []byte) []byte {
	// Check if error marking is enabled via environment variable
	markErrors := os.Getenv("MARK_SQL_ERRORS_AS_ERROR")
	if markErrors != "true" && markErrors != "1" {
		return response
	}

	var mcpResp MCPResponse
	if err := json.Unmarshal(response, &mcpResp); err != nil {
		return response
	}

	// Only process if there's a result
	if len(mcpResp.Result) == 0 {
		return response
	}

	var result MCPResult
	if err := json.Unmarshal(mcpResp.Result, &result); err != nil {
		return response
	}

	// Check if already marked as error
	if result.IsError {
		return response
	}

	// Check content for Oracle errors
	hasOracleError := false
	for _, content := range result.Content {
		if content.Type == "text" && (errorPattern.MatchString(content.Text) ||
			strings.Contains(content.Text, "Error:")) {
			hasOracleError = true
			log.Printf("[sqlcl] Detected Oracle error in response: %s", content.Text)
			break
		}
	}

	if hasOracleError {
		result.IsError = true
		newResult, _ := json.Marshal(result)
		mcpResp.Result = newResult
		newResponse, _ := json.Marshal(mcpResp)
		return newResponse
	}

	return response
}

func main() {
	if err := mcpproxy.Run(mcpproxy.Config{
		ServerName:         "sqlcl",
		CommandPath:        "/opt/oracle/sqlcl/bin/sql",
		CommandArgs:        []string{"-mcp"},
		PathEnvVar:         "SQL_PATH",
		ResponseMiddleware: markOracleErrors,
	}); err != nil {
		log.Fatalf("Failed to run proxy: %v", err)
	}
}
