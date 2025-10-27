# MCP Servers Helm Chart

This Helm chart deploys MCP (Model Context Protocol) servers that provide external tools and capabilities to AI models. MCP servers enable AI agents to interact with external systems, APIs, and services.

## Architecture Overview

The mcp-servers chart supports **flexible deployment modes**:
- **With Toolhive Operator** (recommended): Uses MCPServer CRDs with automated proxy management
- **Without Toolhive**: Falls back to standard Kubernetes Deployments and Services
- **Automatic Detection**: Chart automatically detects Toolhive availability and adapts

### Deployment Resources Created

Depending on Toolhive availability and configuration, the chart creates:
- **MCPServer Custom Resources**: When Toolhive is available (operator-managed)
- **Deployments + Services**: When Toolhive is not available (standard Kubernetes resources)
- **Secure Credential Management**: Integration with Kubernetes secrets
- **Resource Labels**: All resources tagged with `app.kubernetes.io/component: mcp-server` for easy discovery

### Key Components

1. **Oracle SQLcl MCP**: Database interaction capabilities using Oracle's SQLcl
2. **Weather MCP**: External weather API integration
3. **Secure Secret Management**: Credentials sourced from Kubernetes secrets
4. **Flexible Architecture**: Adapts to cluster capabilities automatically

### Deployment Architecture

This chart supports multiple deployment modes for maximum flexibility:

#### Deployment Mode: `auto` (Default - Recommended)
Automatically detects Toolhive availability:
- **If Toolhive is installed**: Creates MCPServer CRDs with operator management
- **If Toolhive is not installed**: Creates standard Deployments and Services
- **Zero configuration required**: Works out of the box in any cluster

#### Deployment Mode: `mcpserver` (Toolhive Required)
Forces MCPServer CRD deployment:
- **Oracle SQLcl MCP**: Uses `transport: stdio` with Toolhive proxy
  - Toolhive automatically proxies stdio to HTTP/SSE for web access
  - Accessible at: `http://mcp-oracle-sqlcl-proxy:8080/sse`
- **Weather MCP**: Uses `transport: sse` with Toolhive management
  - Native SSE transport with Toolhive proxy management
  - Accessible at: `http://mcp-mcp-weather-proxy:8000/sse`

**Benefits:**
- Unified deployment model for all MCP servers
- Automatic proxy and service account management
- Advanced features like permission profiles

#### Deployment Mode: `deployment` (Standard Kubernetes)
Forces standard Deployment + Service resources:
- **Oracle SQLcl MCP**: Deployed as standard Kubernetes Deployment
- **Weather MCP**: Deployed as standard Kubernetes Deployment + Service
- Works in any Kubernetes cluster without additional operators

**Benefits:**
- No operator dependencies
- Standard Kubernetes resource management
- Simpler troubleshooting with familiar resources
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
- **Toolhive Operator**: Required only for MCPServer CRD deployment mode
  - If not installed, chart automatically uses standard Deployments
  - Install from: `oci://ghcr.io/stacklok/toolhive/toolhive-operator`
- **Oracle database**: Required only if enabling Oracle SQLcl MCP server

## Installation

### Quick Start (No Toolhive)

The simplest way to get started - works in any Kubernetes cluster:

```bash
# Install MCP Servers with standard Deployments (no Toolhive required)
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
# Create values file with v0.4.0 images
# Note: v0.4.0 refers to the Toolhive operator application version (not Helm chart version)
cat > /tmp/toolhive-install.yaml << 'EOF'
operator:
  image: ghcr.io/stacklok/toolhive/operator:v0.4.0  # Toolhive operator app version
  toolhiveRunnerImage: ghcr.io/stacklok/toolhive/proxyrunner:v0.4.0  # Toolhive runner app version
EOF

# Install with OpenShift-specific configuration
# Note: --version 0.3.0 is the Helm chart version (different from app version)
# The values-openshift.yaml file is required for OpenShift deployments
helm install toolhive-operator \
  oci://ghcr.io/stacklok/toolhive/toolhive-operator \
  --namespace toolhive-system \
  --version 0.3.0 \
  --values https://raw.githubusercontent.com/stacklok/toolhive/c7ef74ab08388f5c5add962d5e20e04da9c518c6/deploy/charts/operator/values-openshift.yaml \
  --values /tmp/toolhive-install.yaml \
  --wait

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
# 1. Install Toolhive CRDs (OPTIONAL - only needed for MCPServer CRD mode)
helm install toolhive-operator-crds \
  toolhive/toolhive-operator-crds \
  --namespace toolhive-system \
  --version 0.0.42 \
  --wait

# 2. Create values file with v0.4.0 images
# Note: v0.4.0 refers to the Toolhive operator application version (not Helm chart version)
cat > /tmp/toolhive-install.yaml << 'EOF'
operator:
  image: ghcr.io/stacklok/toolhive/operator:v0.4.0  # Toolhive operator app version
  toolhiveRunnerImage: ghcr.io/stacklok/toolhive/proxyrunner:v0.4.0  # Toolhive runner app version
EOF

# 3. Install Toolhive Operator with OpenShift-specific configuration
# Note: --version 0.3.0 is the Helm chart version (different from app version)
# The values-openshift.yaml file is required for OpenShift deployments
helm install toolhive-operator \
  toolhive/toolhive-operator \
  --namespace toolhive-system \
  --version 0.3.0 \
  --values https://raw.githubusercontent.com/stacklok/toolhive/c7ef74ab08388f5c5add962d5e20e04da9c518c6/deploy/charts/operator/values-openshift.yaml \
  --values /tmp/toolhive-install.yaml \
  --wait

# 4. Install MCP Servers (auto-detects Toolhive)
helm install mcp-servers ./helm --namespace <your-namespace> --create-namespace

# 5. Check deployment status
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
- **Secret Management**: Secure credential injection via `envSecrets`
- **Persistent Storage**: Optional volumes and PVCs
- **Security Contexts**: Restricted permissions and SCC bindings
- **Resource Limits**: CPU and memory management
- **Resource Labels**: All resources tagged with `app.kubernetes.io/component: mcp-server`
- **Auto-Discovery**: Works in any Kubernetes environment

## Security
### Credential Management

This chart implements secure credential management:

- **No hardcoded passwords**: All sensitive data sourced from Kubernetes secrets
- **Secret references**: Uses `envSecrets` pattern for secure credential injection
- **Oracle integration**: Leverages Oracle database's own secret for credentials
- **API key management**: Allows secure injection of external API keys

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

4. **Toolhive Operator OOMKilled**: Reinstall with v0.4.0 images and proper resource settings
   ```bash
   # Create values file with v0.4.0 images
   cat > /tmp/toolhive-install.yaml << 'EOF'
   operator:
     image: ghcr.io/stacklok/toolhive/operator:v0.4.0
     toolhiveRunnerImage: ghcr.io/stacklok/toolhive/proxyrunner:v0.4.0
   EOF
   
   # Reinstall with OpenShift configuration and v0.4.0
   helm upgrade toolhive-operator \
     oci://ghcr.io/stacklok/toolhive/toolhive-operator \
     -n toolhive-system \
     --version 0.3.0 \
     --values https://raw.githubusercontent.com/stacklok/toolhive/c7ef74ab08388f5c5add962d5e20e04da9c518c6/deploy/charts/operator/values-openshift.yaml \
     --values /tmp/toolhive-install.yaml
   ```

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
oc get secret oracle23ai -o jsonpath='{.data}' | jq 'keys'

# Check SCC permissions (OpenShift with Toolhive)
oc get clusterrolebindings | grep mcp-servers
oc describe clusterrolebinding mcp-servers-toolhive-operator-anyuid

# Oracle-specific troubleshooting
oc logs oracle23ai-0 | grep -E "(ORA-27350|cannot set groups)"
oc get scc oracle23ai-scc -o jsonpath='{.allowedCapabilities}'
oc describe scc oracle23ai-scc | grep -A 5 "Required Drop Capabilities"
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