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
        ORACLE_USER: "sales"
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
        ORACLE_USER: "sales"
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
3. **Permission Denied**: Verify SCC permissions for service accounts
4. **Image Pull Errors**: Check image tags and registry access

### Debug Commands

```bash
# Check Toolhive operator logs
kubectl logs -l app.kubernetes.io/name=toolhive-operator

# Check MCPServer resources
kubectl get mcpservers -o yaml

# Verify secrets
kubectl get secret oracle23ai -o jsonpath='{.data}' | jq 'keys'
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