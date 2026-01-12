# MCP Servers Helm Chart

This Helm chart deploys MCP (Model Context Protocol) servers that provide external tools and capabilities to AI models. MCP servers enable AI agents to interact with external systems, APIs, and services.

## Architecture Overview

The mcp-servers chart deploys MCP servers as standard Kubernetes Deployments:
- **Standard Kubernetes Resources**: Uses Deployments and Services
- **No Operator Dependencies**: Works in any Kubernetes cluster
- **Built-in HTTP Support**: Oracle SQLcl includes native HTTP proxy

### Deployment Resources Created

The chart creates:
- **Deployments**: Standard Kubernetes workloads
- **Services**: HTTP endpoints for MCP clients
- **Secret Mounts**: Secure credential management
- **Resource Labels**: All resources tagged with `app.kubernetes.io/component: mcp-server` for easy discovery

### Key Components

1. **Oracle SQLcl MCP**: Database interaction capabilities using Oracle's SQLcl with built-in HTTP proxy
   - Native streamable-http transport support
   - No external proxy required
   - Go-based HTTP server manages stdio communication with SQLcl
2. **Weather MCP**: External weather API integration
3. **Secure Secret Management**: Credentials sourced from Kubernetes secrets
4. **Standard Kubernetes Deployments**: Simple, operator-free architecture

### Deployment Architecture

Oracle SQLcl MCP uses a built-in Go HTTP proxy:
- **SQLcl Process**: Runs `sql -mcp` with stdio transport
- **Go HTTP Proxy**: Converts between HTTP (streamable-http) and stdio
- **Multiple Clients**: Proxy handles concurrent HTTP connections
- **No Toolhive Required**: Self-contained architecture

```
HTTP Clients → Go Proxy (port 8080) → SQLcl (stdio) → Oracle DB
```
## Included Files

| File | Description |
|------|-------------|
| `helm/` | Helm chart for MCP servers deployment |
| `oracle-sqlcl/` | Oracle SQLcl MCP container source |
| `weather/` | Weather MCP container source code |
| `README.md` | This documentation |

## Prerequisites

### Required
- Kubernetes or OpenShift cluster (4.12+)
- Helm 3.x
- Access to container registries
- Network connectivity to external APIs

### Optional
- **Oracle database**: Required only if enabling Oracle SQLcl MCP server
- **Oracle user secrets**: OpenShift secrets containing database credentials

## Installation

### Quick Start

```bash
# Install MCP Servers
helm install mcp-servers ./helm --namespace <your-namespace> --create-namespace

# Check deployment status
oc get pods -l app.kubernetes.io/component=mcp-server -n <your-namespace>
oc get deployments -l app.kubernetes.io/component=mcp-server -n <your-namespace>
oc get services -l app.kubernetes.io/component=mcp-server -n <your-namespace>
```

**What gets deployed:**
- ✅ Weather MCP server as Deployment + Service (enabled by default)
- ⏸️ Oracle SQLcl MCP server (disabled by default)

### Installation with Toolhive (Optional - Advanced Features)

For enhanced features like automatic proxy management and permission profiles:

#### Dependency Hierarchy

```
1. Infrastructure Prerequisites
   ├── Kubernetes/OpenShift cluster (4.12+)
   ├── Helm 3.x
   └── Container registry access

2. Toolhive Operator (OPTIONAL)
   ├── Toolhive CRDs installation
   ├── Operator deployment in toolhive-system namespace
   └── RBAC permissions

3. MCP Servers
   ├── Weather MCP (enabled by default)
   └── Oracle SQLcl MCP (disabled by default)
```

#### Installation Sequence

**Step 1: Install Toolhive CRDs (OPTIONAL)**
```bash
# Install Toolhive CRDs (OPTIONAL - for MCPServer CRD support)
helm upgrade -i toolhive-operator-crds \
  -n toolhive-system \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator-crds \
  --create-namespace
```

**Step 2: Install Toolhive Operator (OPTIONAL)**

**OpenShift Installation:**
```bash
# Install Toolhive operator with OpenShift defaults
helm upgrade -i toolhive-operator \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator \
  -n toolhive-system --create-namespace \
  --set operator.podSecurityContext.seccompProfile.type=RuntimeDefault \
  --set operator.containerSecurityContext.runAsUser=null \
  --set operator.resources.limits.memory=384Mi \
  --set operator.resources.requests.memory=192Mi

# Verify Toolhive operator is running
oc get pods -n toolhive-system
```

**Step 3: Install MCP Servers**
```bash
# Install MCP servers (will auto-detect Toolhive and use MCPServer CRDs if available)
helm install mcp-servers ./helm --namespace <your-namespace> --create-namespace

# Verify MCP servers are running
# If Toolhive is installed:
oc get mcpservers -n <your-namespace>
oc get pods -l toolhive=true -n <your-namespace>

# If Toolhive is not installed:
oc get deployments -l app.kubernetes.io/component=mcp-server -n <your-namespace>
oc get services -l app.kubernetes.io/component=mcp-server -n <your-namespace>
```

### Complete Installation Example (with Toolhive)
```bash
# 1. Install Toolhive CRDs and Operator (OPTIONAL - only needed for MCPServer CRD mode)
helm upgrade -i toolhive-operator-crds \
  -n toolhive-system \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator-crds \
  --create-namespace

helm upgrade -i toolhive-operator \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator \
  -n toolhive-system --create-namespace \
  --set operator.podSecurityContext.seccompProfile.type=RuntimeDefault \
  --set operator.containerSecurityContext.runAsUser=null \
  --set operator.resources.limits.memory=384Mi \
  --set operator.resources.requests.memory=192Mi

# 2. Install MCP Servers (auto-detects Toolhive)
helm install mcp-servers ./helm --namespace <your-namespace> --create-namespace

# 3. Check deployment status
oc get mcpservers -n <your-namespace>
oc get pods -l toolhive=true -n <your-namespace>
```

## Configuration

### MCP Servers Configuration

This chart uses a **dynamic, configuration-driven approach** where all MCP servers are automatically generated from the `mcp-servers` section in values.yaml.

#### Key Innovation: Zero-Template Changes Required

Adding new MCP servers requires **only configuration changes** - no template modifications needed:

- **Dynamic Resource Generation**: Templates automatically iterate over your configuration
- **Flexible Deployment**: Automatic adaptation to Toolhive availability
- **Automatic Features**: Resource labeling, monitoring, and service discovery

#### Deployment Mode Configuration

Each MCP server supports three deployment modes:

```yaml
mcp-servers:
  <server-name>:
    enabled: true
    deploymentMode: auto  # auto (default), mcpserver, or deployment
    image: "registry/image:tag"
    port: 8080
    transport: "stdio|sse"
    # ... additional configuration
```

**Deployment Mode Options:**
- **`auto`** (default): Automatically uses MCPServer if Toolhive is available, otherwise uses Deployment
- **`mcpserver`**: Always use MCPServer CRD (requires Toolhive installed)
- **`deployment`**: Always use standard Kubernetes Deployment (works without Toolhive)

#### Configuration Reference

**See `helm/values.yaml` for complete configuration examples** including:

- **Weather MCP Server**: SSE transport with deploymentMode configuration
- **Oracle SQLcl MCP Server**: stdio transport with persistence and secrets
- **Deployment Flexibility**: Works with or without Toolhive operator

#### Supported Features

- **Flexible Deployment**: Automatic adaptation to cluster capabilities
- **Transport Protocols**: Both `stdio` and `sse` (with or without Toolhive)
- **Secret Management**: Automatic Oracle database credential injection via `oracleSecret`
- **Persistent Storage**: Optional volumes and PVCs
- **Security Contexts**: Restricted permissions and SCC bindings
- **Resource Limits**: CPU and memory management
- **Resource Labels**: All resources tagged with `app.kubernetes.io/component: mcp-server`
- **Auto-Discovery**: Works in any Kubernetes environment

#### Oracle Database Integration

The Oracle SQLcl MCP server integrates seamlessly with the oracle-db Helm chart through Kubernetes secrets:

```yaml
mcp-servers:
  oracle-sqlcl:
    enabled: true
    proxyMode: streamable-http  # Use streamable-http for Toolhive
    oracleUserSecrets:           # List of Oracle user secrets to mount
      - oracle-db-user-sales
      - oracle-db-user-sales-reader
```

**How it works:**
1. The oracle-db Helm chart creates per-user secrets (e.g., `oracle-db-user-sales-reader`)
2. Each secret contains: `username`, `password`, `host`, `port`, `serviceName`
3. The mcp-servers template mounts all specified secrets to `/user-secrets/<secret-name>`
4. The startup script automatically creates saved connections for each mounted user
5. Each connection uses the username as the connection alias

**No manual configuration required** - just list the secret names!

## Security
### Credential Management

This chart implements secure credential management:

- **No hardcoded passwords**: All sensitive data sourced from Kubernetes secrets
- **Automatic secret mapping**: Uses `oracleSecret` pattern for streamlined credential injection
- **Oracle integration**: Seamlessly leverages Oracle database user secrets created by oracle-db Helm chart
- **Standardized environment variables**: All Oracle credentials use `ORACLE_*` prefix (ORACLE_USER, ORACLE_PWD, ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE)
- **API key management**: Allows secure injection of external API keys via `env` configuration

### Security Context

All containers run with restricted security contexts:
- `allowPrivilegeEscalation: false`
- `capabilities.drop: [ALL]`
- Proper service account permissions

## Monitoring

### Check MCP Server Status

```bash
# Find all MCP server resources using the component label
oc get all -l app.kubernetes.io/component=mcp-server

# If using Toolhive (MCPServer CRDs):
oc get mcpservers
oc describe mcpserver weather
oc logs -l toolhive-name=weather

# If using standard Deployments:
oc get deployments -l app.kubernetes.io/component=mcp-server
oc get services -l app.kubernetes.io/component=mcp-server
oc describe deployment weather
oc logs -l app.kubernetes.io/name=weather
```

### Health Endpoints

**With Toolhive (MCPServer CRDs):**
- Health: `http://<service-proxy>:8080/health`
- SSE: `http://<service-proxy>:8080/sse`
- JSON-RPC: `http://<service-proxy>:8080/messages`

**Without Toolhive (Standard Deployments):**
- Service endpoints depend on server configuration
- Weather: `http://weather:8000/` (SSE endpoint)

## Troubleshooting

### Common Issues

1. **Wrong Deployment Mode**: Check if resources are created as expected:
   - Run `oc get all -l app.kubernetes.io/component=mcp-server` to see all resources
   - If Toolhive is installed but Deployments are created, check `deploymentMode` setting
   - If MCPServers are attempted without Toolhive, install Toolhive or set `deploymentMode: deployment`

2. **Pod Restarts**: Check health probe timing for database connections

3. **Secret Not Found**: Ensure Oracle secret exists before installing

4. **Toolhive Operator OOMKilled**: Increase memory limits to 1Gi (default 128Mi is insufficient)

5. **MCP Server Pods Not Starting (Toolhive mode)**: Verify SCC permissions were automatically created by checking ClusterRoleBindings

6. **Permission Denied**: Check that SCC bindings exist with `oc get clusterrolebindings | grep mcp-servers`

7. **Oracle Platform Compatibility**: Oracle :latest may have ORA-27350 platform issues - use 23.5.0.0 instead

8. **Oracle Security Context Issues**: Oracle requires SETUID/SETGID capabilities in SCC for proper operation

9. **Storage Issues**: Check PVC creation and storage class availability

10. **Image Pull Errors**: Check image tags and registry access

### Debug Commands

```bash
# Check what deployment mode is being used
oc get all -l app.kubernetes.io/component=mcp-server

# For Toolhive mode:
oc logs -l app.kubernetes.io/name=toolhive-operator -n toolhive-system
oc get mcpservers -o yaml
oc get deployments -l toolhive=true
oc get pods -l toolhive=true
oc describe pod -l toolhive-name=weather

# For standard Deployment mode:
oc get deployments -l app.kubernetes.io/component=mcp-server
oc get services -l app.kubernetes.io/component=mcp-server
oc describe deployment weather
oc logs -l app.kubernetes.io/name=weather

# Verify secrets
oc get secret oracle-db -o jsonpath='{.data}' | jq 'keys'

# Check SCC permissions (OpenShift with Toolhive)
oc get clusterrolebindings | grep mcp-servers
oc describe clusterrolebinding mcp-servers-toolhive-operator-anyuid

# Oracle-specific troubleshooting
oc logs oracle-db-0 | grep -E "(ORA-27350|cannot set groups)"
oc get scc oracle-db-scc -o jsonpath='{.allowedCapabilities}'
oc describe scc oracle-db-scc | grep -A 5 "Required Drop Capabilities"
```

## Adding New MCP Servers

**The power of our optimized architecture**: Adding new MCP servers is entirely configuration-driven.

### Process (3 Simple Steps)

1. **Add configuration** to `values.yaml` (copy pattern from existing servers)
2. **Deploy**: `helm upgrade mcp-servers ./helm --namespace <your-namespace>`
3. **Done!** All resources auto-generated

### What Happens Automatically

- ✅ **Deployment Resources**: MCPServer CRDs or Deployments+Services based on mode
- ✅ **Resource Labels**: All resources tagged with `app.kubernetes.io/component: mcp-server`
- ✅ **Storage**: PVCs created if persistence enabled
- ✅ **Monitoring**: Health endpoints accessible via services
- ✅ **Security**: Restricted contexts and proper labeling applied
- ✅ **Flexibility**: Automatic adaptation to cluster capabilities

**Zero template changes required** - this is the result of our dynamic template optimization.

## Contributing

1. **Support flexible deployment**: Ensure templates work with and without Toolhive
2. **Use dynamic template patterns**: Templates automatically iterate over `mcp-servers` configuration
3. **Maintain deployment mode support**: Test all three modes (auto, mcpserver, deployment)
4. **Implement secure credential management**: Use `envSecrets` for sensitive data
5. **Add appropriate resource limits and security contexts**: Include in server configuration
6. **Use standard labels**: Tag all resources with `app.kubernetes.io/component: mcp-server`
7. **Update this README**: Document new server examples and configuration
8. **Test thoroughly**: Validate with `helm template` and `helm lint` (with and without Toolhive)

### Chart Architecture Principles

This chart follows these key principles:

- **Flexible Deployment**: Works with or without Toolhive operator
- **Dynamic Generation**: Templates iterate over configuration rather than hardcoding server lists
- **Automatic Adaptation**: Detects cluster capabilities and adapts accordingly
- **Standard Labels**: All resources tagged for easy discovery
- **Security by Default**: Restricted security contexts and SCC permissions
- **Maintainability**: Adding new servers requires only configuration changes, no template updates

## Support

For issues and questions:
- Check Toolhive operator documentation
- Review MCPServer CRD specifications
- Verify OpenShift security requirements