# Playground Helm Chart

A Helm chart for integrating hub-deployed resources with the RHOAI Gen AI Studio Playground UI. It registers MCP servers and external model endpoints with the Playground, and optionally configures dashboard feature flags via `OdhDashboardConfig`.

## Overview

This chart does **not** deploy any workloads. Instead, it creates ConfigMaps and Secrets that register existing resources with the Gen AI Studio Playground:

- **MCP Server Registration**: Creates a ConfigMap (`gen-ai-aa-mcp-servers`) that tells the Playground about available MCP servers
- **External Model Endpoints**: Creates a ConfigMap (`gen-ai-aa-custom-model-endpoints`) and Secrets that pre-register external OpenAI-compatible models (Gemini, OpenAI, Anthropic, etc.)
- **Dashboard Configuration**: Optionally creates an `OdhDashboardConfig` CR to enable Gen AI Studio features

## Prerequisites

- OpenShift cluster with RHOAI 3.4+ installed
- Gen AI Studio Playground enabled (`genAiStudio: true` in dashboard config)
- For external models: outbound network access to the provider API (e.g. `generativelanguage.googleapis.com`)

## Installation

### As a dependency in a parent chart

Add to your `Chart.yaml`:

```yaml
dependencies:
  - name: playground
    version: 0.0.1
    repository: https://rh-ai-quickstart.github.io/ai-architecture-charts
    condition: playground.enabled
```

Then configure in your `values.yaml`:

```yaml
playground:
  enabled: true
  dashboardConfig:
    enabled: true
  genAiStudio: true
  aiAssetCustomEndpoints: true
  externalProviders: true
  mcpServers:
    servers:
      - name: My-MCP-Server
        url: "http://my-mcp-server.{{ .Release.Namespace }}.svc:8000/mcp/"
        description: My MCP server description
  customEndpoints:
    enabled: true
    endpoints:
      - modelId: gemini-2.5-flash
        displayName: Gemini 2.5 Flash
        url: https://generativelanguage.googleapis.com/v1beta/openai/
        apiKey: ""
```

Provide the API key at install time:

```bash
helm upgrade --install <release-name> ./helm \
  --set playground.customEndpoints.endpoints[0].apiKey=<your-api-key>
```

### Standalone installation

```bash
helm install playground ./helm \
  --set dashboardConfig.enabled=true \
  --set playground.genAiStudio=true \
  --set playground.aiAssetCustomEndpoints=true \
  --set playground.externalProviders=true
```

## Configuration

### Dashboard Feature Flags

| Parameter | Description | Default |
|-----------|-------------|---------|
| `dashboardConfig.enabled` | Create the OdhDashboardConfig CR (requires RHOAI operator) | `false` |
| `playground.genAiStudio` | Enable Gen AI Studio in the dashboard | `false` |
| `playground.aiAssetCustomEndpoints` | Enable custom endpoint creation | `false` |
| `playground.externalProviders` | Allow third-party provider endpoints (OpenAI, Gemini, etc.) | `false` |
| `playground.externalVectorStores` | Enable external vector store connections | `false` |
| `playground.mcpCatalog` | Enable MCP catalog in the dashboard | `false` |
| `playground.mlflow` | Enable MLflow integration | `false` |
| `playground.modelAsService` | Enable Models-as-a-Service | `false` |

### MCP Server Registration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mcpServers.enabled` | Create the MCP servers ConfigMap | `true` |
| `mcpServers.namespace` | Namespace for the ConfigMap | `redhat-ods-applications` |
| `mcpServers.servers` | List of MCP server entries | `[]` |
| `mcpServers.servers[].name` | Display name (ConfigMap key) | |
| `mcpServers.servers[].url` | Server URL (supports `tpl` expansion) | |
| `mcpServers.servers[].description` | Optional description | |

### Custom External Model Endpoints

| Parameter | Description | Default |
|-----------|-------------|---------|
| `customEndpoints.enabled` | Create the external endpoints ConfigMap and Secrets | `false` |
| `customEndpoints.namespace` | Namespace for resources (defaults to release namespace) | `""` |
| `customEndpoints.endpoints` | List of external model endpoints | `[]` |
| `customEndpoints.endpoints[].modelId` | Model ID as recognized by the provider | |
| `customEndpoints.endpoints[].displayName` | Friendly name shown in the Playground UI | |
| `customEndpoints.endpoints[].url` | Provider API base URL | |
| `customEndpoints.endpoints[].apiKey` | API key (provide via `--set` at install time) | `""` |
| `customEndpoints.endpoints[].providerType` | Provider type identifier | `remote::openai` |
| `customEndpoints.endpoints[].modelType` | Model type | `llm` |

## Resources Created

| Template | Resource | Namespace | Condition |
|----------|----------|-----------|-----------|
| `playground.yaml` | `OdhDashboardConfig` | `redhat-ods-applications` | `dashboardConfig.enabled` |
| `mcp-servers-configmap.yaml` | ConfigMap `gen-ai-aa-mcp-servers` | `redhat-ods-applications` | `mcpServers.enabled` and servers non-empty |
| `custom-endpoints-configmap.yaml` | ConfigMap `gen-ai-aa-custom-model-endpoints` | Release namespace | `customEndpoints.enabled` and endpoints non-empty |
| `custom-endpoints-secrets.yaml` | Secret `endpoint-api-key-N` (one per endpoint) | Release namespace | `customEndpoints.enabled` and `apiKey` non-empty |

## Examples

### Register MCP servers only (no external models)

```yaml
playground:
  enabled: true
  mcpServers:
    servers:
      - name: GitHub-MCP
        url: "https://api.githubcopilot.com/mcp/x/repos/readonly"
        description: GitHub repository access
```

### External model with Gemini

```yaml
playground:
  enabled: true
  dashboardConfig:
    enabled: true
  genAiStudio: true
  aiAssetCustomEndpoints: true
  externalProviders: true
  customEndpoints:
    enabled: true
    endpoints:
      - modelId: gemini-2.5-flash
        displayName: Gemini 2.5 Flash
        url: https://generativelanguage.googleapis.com/v1beta/openai/
        apiKey: ""
```

## Security Notes

- API keys are stored in Kubernetes Secrets, never in ConfigMaps or source code
- The `apiKey` field in `values.yaml` should always be empty (`""`) -- provide keys via `--set` at deploy time
- Enabling `externalProviders` allows data (RAG context, MCP tool results, user input) to be sent outside the cluster

## Uninstall

```bash
helm uninstall playground
```
