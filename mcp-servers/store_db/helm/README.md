# MCP DBStore Helm Chart

A Helm chart for deploying the MCP DBStore server with PostgreSQL database on Kubernetes.

## Overview

This chart deploys a complete Model Context Protocol (MCP) server that provides database-backed product inventory tools. The deployment includes:

- **MCP DBStore Server**: FastMCP-based server with 7 inventory management tools
- **PostgreSQL Database**: Persistent database with sample data initialization
- **Service Discovery**: Kubernetes services for internal cluster communication
- **Security**: RBAC, security contexts, and secret management

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (for PostgreSQL persistence)

## Installation

### Quick Start

```bash
# Install from local chart
helm install my-mcp-dbstore ./helm/mcp-dbstore
```

### Custom Installation

```bash
# Install with custom values
helm install my-mcp-dbstore ./helm/mcp-dbstore \
  --set postgresql.auth.password=mysecretpassword \
  --set mcpServer.image.tag=latest \
  --set postgresql.persistence.size=5Gi

# Install in custom namespace
kubectl create namespace mcp-servers
helm install my-mcp-dbstore ./helm/mcp-dbstore -n mcp-servers
```

## Usage

### Accessing the MCP Server

After installation, you can access the MCP server:

```bash
# Port forward to access from local machine
kubectl port-forward svc/my-mcp-dbstore-mcp-server 8002:8002

# Test connection
curl http://localhost:8002/health
```

### Using MCP Inspector

```bash
# Install MCP inspector
pip install mcp-inspector

# Inspect the server tools
mcp-inspector http://localhost:8002
```

### Database Access

```bash
# Port forward PostgreSQL
kubectl port-forward svc/my-mcp-dbstore-postgresql 5432:5432

# Get database password
kubectl get secret my-mcp-dbstore-postgresql -o jsonpath="{.data.password}" | base64 --decode

# Connect with psql
psql -h localhost -U mcpuser -d store_db
```

## Available Tools

The MCP server provides these tools for LLM agents:

1. **get_products** - Retrieve paginated product list
2. **get_product_by_id** - Get specific product details
3. **get_product_by_name** - Find product by exact name
4. **search_products** - Search products by query string
5. **add_product** - Create new product in inventory
6. **remove_product** - Delete product by ID
7. **order_product** - Place product order (updates inventory)

## Llama Stack Integration

Register with Llama Stack for agent usage:

```bash
# Register the MCP server
llamastack mcp-server register \
  --name mcp-dbstore \
  --url http://my-mcp-dbstore-mcp-server.default.svc.cluster.local:8002 \
  --description "Product inventory management tools"

# Verify registration
llamastack mcp-server list

# Use in agent configuration
llamastack agent create \
  --name inventory-agent \
  --tool-groups mcp-dbstore
```

## Monitoring

### Health Checks

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=mcp-dbstore

# Check service endpoints
kubectl get endpoints

# View logs
kubectl logs -f deployment/my-mcp-dbstore-mcp-server
kubectl logs -f deployment/my-mcp-dbstore-postgresql
```

### Metrics (if enabled)

```bash
# View service monitor (if monitoring.enabled=true)
kubectl get servicemonitor -l app.kubernetes.io/name=mcp-dbstore
```

## Troubleshooting

### Common Issues

1. **MCP Server won't start**
   ```bash
   # Check init container logs
   kubectl logs deployment/my-mcp-dbstore-mcp-server -c wait-for-db
   
   # Check database connectivity
   kubectl exec -it deployment/my-mcp-dbstore-postgresql -- pg_isready
   ```

2. **Database connection issues**
   ```bash
   # Verify secret exists
   kubectl get secret my-mcp-dbstore-postgresql
   
   # Check database URL
   kubectl get secret my-mcp-dbstore-mcp-server -o yaml
   ```

3. **Persistent volume issues**
   ```bash
   # Check PVC status
   kubectl get pvc
   
   # Check storage class
   kubectl get storageclass
   ```

### Debug Mode

Enable debug logging:

```bash
helm upgrade my-mcp-dbstore ./deploy/helm/mcp-dbstore \
  --set mcpServer.env.PYTHONPATH=/app \
  --set mcpServer.env.LOG_LEVEL=DEBUG
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade my-mcp-dbstore ./deploy/helm/mcp-dbstore \
  --set mcpServer.image.tag=0.0.2

# Rollback if needed
helm rollback my-mcp-dbstore 1
```

## Uninstalling

```bash
# Uninstall the release
helm uninstall my-mcp-dbstore

# Clean up PVCs (if needed)
kubectl delete pvc data-my-mcp-dbstore-postgresql-0
```

## Development

### Building Custom Images

```bash
# Build and push MCP server image
docker build -t your-registry/mcp_dbstore:custom ./mcpservers/mcp_dbstore
docker push your-registry/mcp_dbstore:custom

# Use custom image
helm install my-mcp-dbstore ./deploy/helm/mcp-dbstore \
  --set mcpServer.image.registry=your-registry \
  --set mcpServer.image.repository=mcp_dbstore \
  --set mcpServer.image.tag=custom
```

### Local Development

```bash
# Run with development values
helm install dev-mcp-dbstore ./deploy/helm/mcp-dbstore \
  -f ./deploy/helm/mcp-dbstore/values-dev.yaml
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `helm lint` and `helm template`
5. Submit a pull request

## Configuration Reference

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `""` |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]` |
| `global.storageClass` | Global StorageClass for Persistent Volume(s) | `""` |

### MCP Server Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mcpServer.enabled` | Enable MCP server deployment | `true` |
| `mcpServer.image.registry` | MCP server image registry | `quay.io` |
| `mcpServer.image.repository` | MCP server image repository | `skattoju/mcp_dbstore` |
| `mcpServer.image.tag` | MCP server image tag | `0.0.1` |
| `mcpServer.image.pullPolicy` | MCP server image pull policy | `IfNotPresent` |
| `mcpServer.replicaCount` | Number of MCP server replicas | `1` |
| `mcpServer.service.type` | MCP server service type | `ClusterIP` |
| `mcpServer.service.port` | MCP server service port | `8002` |
| `mcpServer.resources.limits.cpu` | MCP server CPU limit | `500m` |
| `mcpServer.resources.limits.memory` | MCP server memory limit | `512Mi` |
| `mcpServer.resources.requests.cpu` | MCP server CPU request | `100m` |
| `mcpServer.resources.requests.memory` | MCP server memory request | `128Mi` |

### PostgreSQL Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL deployment | `true` |
| `postgresql.image.registry` | PostgreSQL image registry | `docker.io` |
| `postgresql.image.repository` | PostgreSQL image repository | `postgres` |
| `postgresql.image.tag` | PostgreSQL image tag | `15-alpine` |
| `postgresql.auth.username` | PostgreSQL username | `mcpuser` |
| `postgresql.auth.password` | PostgreSQL password | `mcppassword` |
| `postgresql.auth.database` | PostgreSQL database name | `store_db` |
| `postgresql.persistence.enabled` | Enable PostgreSQL persistence | `true` |
| `postgresql.persistence.size` | PostgreSQL persistent volume size | `2Gi` |
| `postgresql.persistence.storageClass` | PostgreSQL storage class | `""` |
| `postgresql.initdb.enabled` | Enable database initialization with sample data | `true` |

### Security Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `""` |
| `podSecurityContext.runAsNonRoot` | Run containers as non-root | `true` |
| `securityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |

## License

This Helm chart is licensed under the Apache 2.0 License.

## Support

- GitHub Issues: https://github.com/yourusername/ai-virtual-assistant/issues
- Documentation: https://github.com/yourusername/ai-virtual-assistant/tree/main/mcpservers/mcp_dbstore
- MCP Protocol: https://modelcontextprotocol.io/docs/ 