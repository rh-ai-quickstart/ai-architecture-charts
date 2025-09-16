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
1. Infrastructure Prerequisites
   ├── OpenShift cluster (4.12+)
   ├── Helm 3.x
   └── Container registry access

2. External Dependencies (if using Oracle SQLcl MCP)
   └── Oracle Database
       ├── Database instance running
       ├── Sales schema/user created
       └── Kubernetes secret with credentials

3. Toolhive Operator
   ├── CRDs installation
   ├── Operator deployment
   └── RBAC permissions

4. MCP Servers
   ├── Weather MCP (requires Tavily API key)
   └── Oracle SQLcl MCP (requires Oracle DB + secret)
```

### Installation Sequence

**Step 1: Verify Infrastructure Prerequisites**
```bash
# Verify OpenShift cluster access
oc whoami
oc get nodes

# Verify Helm installation
helm version
```

**Step 2: Deploy External Dependencies (Oracle SQLcl MCP only)**
```bash
# Deploy Oracle database using the Oracle DB chart
helm install oracle-db ../oracle-db/helm --namespace <your-namespace>

# Wait for Oracle database to be ready
oc wait --for=condition=ready pod -l app=oracle23ai --timeout=600s

# Verify Oracle secret was created by the database chart
oc get secret oracle23ai
```

**Step 3: Install Toolhive Operator**
```bash
# Add Toolhive Helm repository
helm repo add toolhive https://stacklok.github.io/toolhive
helm repo update

# Install Toolhive CRDs
helm install toolhive-crds toolhive/toolhive-operator-crds --version 0.0.18

# Install Toolhive operator with adequate memory resources
helm install toolhive-operator toolhive/toolhive-operator --version 0.2.6 --namespace <your-namespace>

# IMPORTANT: Increase memory limits to prevent OOMKilled errors
oc patch deployment toolhive-operator --namespace <your-namespace> --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "1Gi"},
       {"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/memory", "value": "1Gi"}]'

# Grant required SecurityContextConstraints for Toolhive operator
oc adm policy add-scc-to-user anyuid -z toolhive-operator --namespace <your-namespace>

# Verify Toolhive operator is running
oc get pods -l app.kubernetes.io/name=toolhive-operator --namespace <your-namespace>
```

**Step 4: Enable MCP Servers and Grant Required Permissions**
```bash
# Create configuration file to enable both MCP servers
cat > mcp-config.yaml << EOF
toolhive:
  crds:
    enabled: false  # CRDs already exist
  operator:
    enabled: true

mcp-servers:
  mcp-weather:
    mcpserver:
      enabled: true
      env:
        TAVILY_API_KEY: ""  # Add your API key if needed
      permissionProfile:
        name: network
        type: builtin

  oracle-sqlcl:
    mcpserver:
      enabled: true
      env:
        ORACLE_USER: "sales"  # Sales schema user created by Oracle DB chart
        ORACLE_PASSWORD: null  # Sourced from secret
        ORACLE_CONNECTION_STRING: null  # Sourced from secret
        ORACLE_CONN_NAME: "oracle_connection"
      envSecrets:
        ORACLE_PASSWORD:
          name: oracle23ai
          key: password
        ORACLE_CONNECTION_STRING:
          name: oracle23ai
          key: jdbc-uri
      permissionProfile:
        name: network
        type: builtin
    volumes:
      - name: sqlcl-data
        persistentVolumeClaim:
          claimName: oracle-sqlcl-data
    volumeMounts:
      - name: sqlcl-data
        mountPath: /sqlcl-home
EOF

# Create required PVC for Oracle SQLcl MCP server
oc apply -f - << EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: oracle-sqlcl-data
  namespace: <your-namespace>
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: gp3-csi
EOF

# Upgrade Helm release to enable MCP servers
helm upgrade mcp-servers ./helm --namespace <your-namespace> -f mcp-config.yaml

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
helm install mcp-servers ./helm --namespace <your-namespace>
```

### Production Installation with Oracle Database

```bash
# Create configuration file
cat > mcp-config.yaml << EOF
toolhive:
  crds:
    enabled: true
  operator:
    enabled: true

mcp-servers:
  mcp-weather:
    mcpserver:
      enabled: true
      env:
        TAVILY_API_KEY: ""  # Provide your API key
  
  oracle-sqlcl:
    mcpserver:
      enabled: true
      env:
        ORACLE_USER: "sales"  # Sales schema user created by Oracle DB chart
        ORACLE_PASSWORD: null  # Sourced from secret
        ORACLE_CONNECTION_STRING: null  # Sourced from secret
      envSecrets:
        ORACLE_PASSWORD:
          name: oracle23ai
          key: password
        ORACLE_CONNECTION_STRING:
          name: oracle23ai
          key: jdbc-uri
EOF

# Install with configuration
helm install mcp-servers ./helm --namespace <your-namespace> -f mcp-config.yaml
```

## Configuration

### Architecture Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `toolhive.crds.enabled` | Install Toolhive CRDs | `true` |
| `toolhive.operator.enabled` | Deploy Toolhive operator | `true` |
| `toolhive-operator.operator.resources` | Operator resource limits | See values.yaml |

### MCP Server Configuration

#### Weather MCP Server
```yaml
mcp-servers:
  mcp-weather:
    mcpserver:
      enabled: true
      env:
        TAVILY_API_KEY: ""  # Required: Your Tavily API key
      permissionProfile:
        name: network
        type: builtin
      port: 8080
      transport: stdio
    imageRepository: quay.io/ecosystem-appeng/mcp-weather
    imageTag: "0.1.0"
```

#### Oracle SQLcl MCP Server
```yaml
mcp-servers:
  oracle-sqlcl:
    mcpserver:
      enabled: true
      env:
        ORACLE_USER: "sales"  # Sales schema user created by Oracle DB chart
        ORACLE_PASSWORD: null  # Sourced from secret
        ORACLE_CONNECTION_STRING: null  # Sourced from secret
        ORACLE_CONN_NAME: "oracle_connection"
      envSecrets:
        ORACLE_PASSWORD:
          name: oracle23ai  # Name of your Oracle secret
          key: password
        ORACLE_CONNECTION_STRING:
          name: oracle23ai
          key: jdbc-uri
      permissionProfile:
        name: network
        type: builtin
    imageRepository: quay.io/rhkp/oracle-sqlcl-mcp
    imageTag: "1.0.0"
    volumes:
      - name: sqlcl-data
        persistentVolumeClaim:
          claimName: oracle-sqlcl-data
    volumeMounts:
      - name: sqlcl-data
        mountPath: /sqlcl-home
```

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
kubectl get mcpservers

# Check specific server status
kubectl describe mcpserver oracle-sqlcl

# View server logs
kubectl logs -l toolhive-name=oracle-sqlcl
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
7. **Missing PVC**: Ensure oracle-sqlcl-data PVC exists before enabling Oracle SQLcl MCP
8. **Image Pull Errors**: Check image tags and registry access

### Debug Commands

```bash
# Check Toolhive operator logs
kubectl logs -l app.kubernetes.io/name=toolhive-operator

# Check MCPServer resources
kubectl get mcpservers -o yaml

# Verify secrets
kubectl get secret oracle23ai -o jsonpath='{.data}' | jq 'keys'

# Check SCC permissions for service accounts
oc get scc anyuid -o jsonpath='{.users}'
oc describe scc anyuid | grep -A 10 Users

# Verify MCP server deployments and pods
oc get deployments -l toolhive=true
oc get pods -l toolhive=true
oc describe pod -l toolhive-name=mcp-weather
oc describe pod -l toolhive-name=oracle-sqlcl
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