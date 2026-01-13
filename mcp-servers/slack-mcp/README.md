# Slack MCP Server

MCP (Model Context Protocol) server for Slack workspace integration. This uses the upstream [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) image directly, which supports SSE and HTTP transports natively.

> **⚠️ WARNING**: This is a community-maintained Slack MCP server ([korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server)). An official Slack MCP server may be released in the future that would replace this implementation. Monitor the [MCP servers registry](https://github.com/modelcontextprotocol/servers) for official Slack support.

## Features

Based on the upstream [slack-mcp-server](https://github.com/korotovsky/slack-mcp-server):

- **Stealth and OAuth Modes**: Run without requiring bot installations (stealth mode) or use OAuth tokens
- **Multiple Auth Methods**: Supports `xoxc`/`xoxd` (stealth), `xoxp` (user OAuth), and `xoxb` (bot) tokens
- **Native SSE/HTTP Transport**: No proxy wrapper needed - supports streamable HTTP directly
- **DMs and Group DMs**: Access direct messages and group conversations
- **Smart History Fetch**: Retrieve messages by date or count
- **Channel Operations**: List channels, search messages, and more
- **User Cache**: Efficient caching of user information

## Authentication Options

The Slack MCP server supports multiple authentication methods:

### Option 1: Stealth Mode (xoxc + xoxd tokens)
No bot installation required. Extract tokens from browser cookies:
- `SLACK_MCP_XOXC_TOKEN`: Found in browser cookies as `d` cookie
- `SLACK_MCP_XOXD_TOKEN`: Found in localStorage or network requests

### Option 2: User OAuth Token (xoxp)
- `SLACK_MCP_XOXP_TOKEN`: User OAuth token with required scopes

### Option 3: Bot Token (xoxb)
- `SLACK_MCP_XOXB_TOKEN`: Bot token (limited to invited channels only)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_MCP_XOXC_TOKEN` | Yes* | Slack xoxc token (stealth mode) |
| `SLACK_MCP_XOXD_TOKEN` | Yes* | Slack xoxd token (stealth mode) |
| `SLACK_MCP_XOXP_TOKEN` | Yes* | User OAuth token (alternative to xoxc/xoxd) |
| `SLACK_MCP_XOXB_TOKEN` | Yes* | Bot token (alternative, limited access) |
| `SLACK_MCP_PORT` | No | Port for the server (default: 13080) |
| `SLACK_MCP_HOST` | No | Host to bind to (default: 127.0.0.1) |
| `SLACK_MCP_ADD_MESSAGE_TOOL` | No | Enable message posting (`true`, channel list, or `!channel` to exclude) |
| `SLACK_MCP_LOG_LEVEL` | No | Log level: debug, info, warn, error (default: info) |

*One of the token combinations is required: `xoxc`+`xoxd`, `xoxp`, or `xoxb`

## Helm Configuration

Add to your `values.yaml`:

```yaml
mcp-servers:
  slack-mcp:
    enabled: true
    deploymentMode: deployment
    image:
      repository: ghcr.io/korotovsky/slack-mcp-server
      tag: "latest"  # Uses upstream image directly
    transport: sse
    targetPort: 13080  # Default SSE port
    envSecrets:
      # For stealth mode (recommended):
      SLACK_MCP_XOXC_TOKEN:
        name: slack-mcp-secret
        key: SLACK_MCP_XOXC_TOKEN
      SLACK_MCP_XOXD_TOKEN:
        name: slack-mcp-secret
        key: SLACK_MCP_XOXD_TOKEN
      # Or for OAuth mode:
      # SLACK_MCP_XOXP_TOKEN:
      #   name: slack-mcp-secret
      #   key: SLACK_MCP_XOXP_TOKEN
    env:
      SLACK_MCP_HOST: "0.0.0.0"  # Bind to all interfaces for Kubernetes
```

## Creating the Secret

### For Stealth Mode (xoxc + xoxd)

```bash
# Create secret with stealth mode tokens
oc create secret generic slack-mcp-secret \
  --from-literal=SLACK_MCP_XOXC_TOKEN="xoxc-..." \
  --from-literal=SLACK_MCP_XOXD_TOKEN="xoxd-..."
```

### For OAuth Mode (xoxp)

```bash
# Create secret with OAuth token
oc create secret generic slack-mcp-secret \
  --from-literal=SLACK_MCP_XOXP_TOKEN="xoxp-..."
```

## Available Tools

The Slack MCP server provides tools for:

- **channels_list**: List all accessible channels
- **conversations_history**: Get messages from a channel
- **conversations_replies**: Get thread replies
- **conversations_search**: Search messages across channels
- **users_list**: List workspace users
- **conversations_add_message**: Send messages (when enabled)

## Architecture

```
HTTP Clients → slack-mcp-server (SSE port 13080) → Slack API
```

The upstream image supports SSE transport natively, so no proxy wrapper is required.

## References

- [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) - Upstream Slack MCP server
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
