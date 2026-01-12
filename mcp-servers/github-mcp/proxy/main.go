package main

import (
	"log"

	"github.com/rh-ai-kickstart/ai-architecture-charts/mcp-servers/mcpproxy"
)

func main() {
	if err := mcpproxy.Run(mcpproxy.Config{
		ServerName:  "github-mcp",
		CommandPath: "/server/github-mcp-server",
		CommandArgs: []string{"stdio"},
		PathEnvVar:  "GITHUB_MCP_PATH",
		EnableCORS:  true,
	}); err != nil {
		log.Fatalf("Failed to run proxy: %v", err)
	}
}
