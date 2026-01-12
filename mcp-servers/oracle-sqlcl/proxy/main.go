package main

import (
	"log"

	"github.com/rh-ai-kickstart/ai-architecture-charts/mcp-servers/mcpproxy"
)

func main() {
	if err := mcpproxy.Run(mcpproxy.Config{
		ServerName:  "sqlcl",
		CommandPath: "/opt/oracle/sqlcl/bin/sql",
		CommandArgs: []string{"-mcp"},
		PathEnvVar:  "SQL_PATH",
	}); err != nil {
		log.Fatalf("Failed to run proxy: %v", err)
	}
}
