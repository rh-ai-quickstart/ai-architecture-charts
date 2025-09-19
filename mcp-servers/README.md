# MCP Servers Helm Chart

This Helm chart deploys MCP (Model Context Protocol) servers using the Toolhive operator that provides external tools and capabilities to AI models. MCP servers enable AI agents to interact with external systems, APIs, and services.

## Architecture Overview

The mcp-servers chart creates:
- **Toolhive Operator**: Centralized operator for managing MCP servers
- **MCPServer Custom Resources**: Kubernetes-native MCP server definitions
- **Automated Proxy Management**: Toolhive handles networking and communication
- **Secure Credential Management**: Integration with Kubernetes secrets
- **Support for Multiple MCP Types**: Weather services, Oracle SQLcl, and extensible architecture

### Key Components

1. **Toolhive Operator**: Manages the lifecycle of MCP servers
2. **MCPServer CRDs**: Define MCP server specifications declaratively  
3. **Oracle SQLcl MCP**: Database interaction capabilities using Oracle's SQLcl
4. **Weather MCP**: External weather API integration
5. **Secure Secret Management**: Credentials sourced from Kubernetes secrets
## Included Files

| File | Description |
|------|-------------|
| `helm/` | Helm chart for MCP servers deployment |
| `mcp-config.yaml` | Pre-configured values file with working defaults |
| `oracle-sqlcl/` | Oracle SQLcl MCP container source |
| `weather/` | Weather MCP container source code |
| `README.md` | This documentation |

## Prerequisites

- OpenShift cluster (4.12+)
- Helm 3.x
- Access to container registries
- Network connectivity to external APIs
- Oracle database (for Oracle SQLcl MCP server)

## Installation

### Dependency Hierarchy & Installation Sequence

The MCP servers deployment has the following dependency hierarchy that must be followed for proper installation:

```
1. Toolhive CRDs & Infrastructure Prerequisites
   ├── OpenShift cluster (4.12+)
   ├── Helm 3.x
   ├── Container registry access
   └── Toolhive CRDs installation (REQUIRED FIRST)

2. External Dependencies (if using Oracle SQLcl MCP)
   └── Oracle Database
       ├── Database instance running
       ├── Sales schema/user created
       └── Kubernetes secret with credentials

3. Toolhive Operator
   ├── Operator deployment
   └── RBAC permissions

4. MCP Servers
   ├── Weather MCP (requires Tavily API key)
   └── Oracle SQLcl MCP (requires Oracle DB + secret)
```

### Installation Sequence

**Step 1: Install Toolhive CRDs and Verify Prerequisites**
```bash
# Verify OpenShift cluster access
oc whoami
oc get nodes

# Verify Helm installation
helm version

# Add Toolhive Helm repository
helm repo add toolhive https://stacklok.github.io/toolhive
helm repo update

# Install Toolhive CRDs (REQUIRED FIRST for MCP servers)
helm install toolhive-crds toolhive/toolhive-operator-crds --version 0.0.18
```

**Step 2: Deploy External Dependencies (Oracle SQLcl MCP only)**
```bash
# Deploy Oracle database using the Oracle 23ai chart (using 23.5.0.0 for platform compatibility)
helm install oracle-db ../oracle23ai/helm --namespace <your-namespace> --set oracle.image.tag=23.5.0.0

# Wait for Oracle database StatefulSet to be ready
oc wait --for=jsonpath='{.status.readyReplicas}'=1 statefulset/oracle23ai --timeout=600s

# Verify Oracle secret was created by the database chart
oc get secret oracle23ai
```

**Step 3: Install Toolhive Operator**
```bash
# Install Toolhive operator with 1Gi memory (default 128Mi is insufficient)
helm install toolhive-operator toolhive/toolhive-operator --version 0.2.6 --namespace <your-namespace> --set operator.resources.requests.memory=1Gi --set operator.resources.limits.memory=1Gi

# Grant required SecurityContextConstraints for Toolhive operator
oc adm policy add-scc-to-user anyuid -z toolhive-operator --namespace <your-namespace>

# Verify Toolhive operator is running
oc get pods -l app.kubernetes.io/name=toolhive-operator --namespace <your-namespace>
```

**Step 4: Enable MCP Servers and Grant Required Permissions**
```bash
# Install MCP servers using configuration file (operator already installed in Step 3)
# PVC will be created automatically by the helm chart
helm install mcp-servers ./helm --namespace <your-namespace> -f mcp-config.yaml

# Grant SecurityContextConstraints for MCP server service accounts
# IMPORTANT: These are required for MCP server pods to start
oc adm policy add-scc-to-user anyuid -z mcp-weather-proxy-runner --namespace <your-namespace>
oc adm policy add-scc-to-user anyuid -z oracle-sqlcl-proxy-runner --namespace <your-namespace>

# Verify MCP servers are running
oc get pods -l toolhive=true --namespace <your-namespace>
oc get mcpservers --namespace <your-namespace>
```

### Quick Start

```bash
# Install with default configuration (MCPServer resources enabled)
# Note: PVCs are created automatically by the helm chart
helm install mcp-servers ./helm --namespace <your-namespace>
```

### Production Installation with Oracle Database

```bash
# Use the provided configuration file (edit mcp-config.yaml if needed)
# Note: mcp-config.yaml is included in this directory with working defaults
# Update TAVILY_API_KEY if you have one for weather functionality

# Install with configuration (PVCs created automatically)
helm install mcp-servers ./helm --namespace <your-namespace> -f mcp-config.yaml
```

## Configuration

### Architecture Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `toolhive.crds.enabled` | Install Toolhive CRDs | `true` |
| `toolhive.operator.enabled` | Deploy Toolhive operator | `true` |
| `toolhive-operator.operator.resources` | Operator resource limits | See values.yaml |

### Configuration

**All MCP server configurations are provided in `mcp-config.yaml`** with working defaults.

**Key Configuration Notes:**
- **Weather MCP**: Uses `imageTag: "0.1.0"` (latest tag not available)
- **Oracle SQLcl MCP**: Requires Oracle database secret (automatically created by Oracle chart)
- **API Keys**: Update `TAVILY_API_KEY` in mcp-config.yaml if you have one
- **Secrets**: Oracle credentials are automatically sourced from the `oracle23ai` secret

**To customize**: Edit `mcp-config.yaml` before running `helm install`.

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
# List all MCP servers
oc get mcpservers

# Check specific server status
oc describe mcpserver oracle-sqlcl

# View server logs
oc logs -l toolhive-name=oracle-sqlcl
```

### Health Endpoints

MCP servers expose health endpoints through Toolhive proxy:
- Health: `http://<service>:8080/health`
- SSE: `http://<service>:8080/sse`
- JSON-RPC: `http://<service>:8080/messages`

## Troubleshooting

### Common Issues

1. **Pod Restarts**: Check health probe timing for database connections
2. **Secret Not Found**: Ensure Oracle secret exists before installing
3. **Toolhive Operator Not Starting**: Grant anyuid SCC to toolhive-operator service account
4. **Toolhive Operator OOMKilled**: Increase memory limits to 1Gi (default 128Mi is insufficient)
5. **MCP Server Pods Not Starting**: Grant anyuid SCC to MCP server proxy-runner service accounts
6. **Permission Denied**: Verify SCC permissions for service accounts
7. **Oracle Platform Compatibility**: Oracle :latest may have ORA-27350 platform issues - use 23.5.0.0 instead
8. **Oracle Security Context Issues**: Oracle requires SETUID/SETGID capabilities in SCC for proper operation
9. **Storage Issues**: Check PVC creation and storage class availability
10. **Image Pull Errors**: Check image tags and registry access

### Debug Commands

```bash
# Check Toolhive operator logs
oc logs -l app.kubernetes.io/name=toolhive-operator

# Check MCPServer resources
oc get mcpservers -o yaml

# Verify secrets
oc get secret oracle23ai -o jsonpath='{.data}' | jq 'keys'

# Check SCC permissions for service accounts
oc get scc anyuid -o jsonpath='{.users}'
oc describe scc anyuid | grep -A 10 Users

# Verify MCP server deployments and pods
oc get deployments -l toolhive=true
oc get pods -l toolhive=true
oc describe pod -l toolhive-name=mcp-weather
oc describe pod -l toolhive-name=oracle-sqlcl

# Oracle-specific troubleshooting
oc logs oracle23ai-0 | grep -E "(ORA-27350|cannot set groups)"
oc get scc oracle23ai-scc -o jsonpath='{.allowedCapabilities}'
oc describe scc oracle23ai-scc | grep -A 5 "Required Drop Capabilities"
```

## Migration from Legacy Deployment

If migrating from standalone oracle-sqlcl deployment:

1. Uninstall old oracle-sqlcl chart
2. Install this unified mcp-servers chart
3. Configure `oracle-sqlcl.mcpserver.enabled: true`
4. Update secret references

## Contributing

1. Follow existing patterns for new MCP servers
2. Use MCPServer CRDs instead of direct Deployments  
3. Implement secure credential management
4. Add appropriate resource limits and security contexts
5. Update this README with new server documentation

## Support

For issues and questions:
- Check Toolhive operator documentation
- Review MCPServer CRD specifications
- Verify OpenShift security requirements