# MCP DBStore User Guide

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Integration with Llama Stack](#integration-with-llama-stack)
- [Monitoring](#monitoring)

## Overview

The MCP DBStore server is a Model Context Protocol (MCP) server that provides database-backed product inventory management tools for AI agents. It enables LLM agents to interact with a PostgreSQL database through a standardized set of tools for product management operations.

### Key Features

- **7 Inventory Tools**: Complete product lifecycle management
- **FastMCP Framework**: High-performance async MCP server implementation  
- **PostgreSQL Backend**: Persistent, ACID-compliant data storage
- **Kubernetes Ready**: Production-ready Helm chart deployment
- **Auto-Discovery**: Tools automatically discovered by Llama Stack
- **Sample Data**: Pre-populated with demonstration products

### Available Tools

1. **get_products** - Paginated product catalog browsing
2. **get_product_by_id** - Specific product details lookup
3. **get_product_by_name** - Exact name-based product search
4. **search_products** - Flexible text search across products
5. **add_product** - New product creation with validation
6. **remove_product** - Product deletion with safety checks
7. **order_product** - Order processing with automatic inventory updates

## Quick Start

### Prerequisites

- Kubernetes cluster (1.19+)
- Helm 3.2.0+
- kubectl configured for your cluster
- Storage provisioner for persistent volumes

### 1-Minute Deployment

```bash
# Clone repository
git clone https://github.com/yourusername/ai-virtual-assistant.git
cd ai-virtual-assistant

# Deploy with Helm
helm install mcp-dbstore ./deploy/helm/mcp-dbstore

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=mcp-dbstore --timeout=300s

# Check deployment status
kubectl get pods -l app.kubernetes.io/name=mcp-dbstore
```

Expected output:
```
NAME                                        READY   STATUS    RESTARTS   AGE
mcp-dbstore-mcp-server-5d4f8b7c9d-xyz123   1/1     Running   0          2m
mcp-dbstore-postgresql-6b8c4d5e7f-abc456   1/1     Running   0          2m
```

### First Test

```bash
# Port forward to access MCP server
kubectl port-forward svc/mcp-dbstore-mcp-server 8002:8002 &

# Install MCP inspector
pip install mcp-inspector

# Explore available tools
mcp-inspector http://localhost:8002
```

## Installation

### Standard Installation

```bash
# Install in default namespace
helm install my-inventory ./deploy/helm/mcp-dbstore

# Install in custom namespace
kubectl create namespace mcp-servers
helm install my-inventory ./deploy/helm/mcp-dbstore -n mcp-servers
```

### Production Installation

```bash
# Production deployment with custom values
helm install production-inventory ./deploy/helm/mcp-dbstore \
  --set postgresql.auth.password="$(openssl rand -base64 32)" \
  --set postgresql.persistence.size=10Gi \
  --set postgresql.persistence.storageClass=ssd \
  --set mcpServer.resources.limits.memory=1Gi \
  --set mcpServer.resources.limits.cpu=1000m \
  --set mcpServer.replicaCount=2
```

### High Availability Setup

```bash
# Multi-replica deployment
helm install ha-inventory ./deploy/helm/mcp-dbstore \
  --set mcpServer.replicaCount=3 \
  --set postgresql.persistence.size=20Gi \
  --set mcpServer.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].weight=100 \
  --set mcpServer.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.labelSelector.matchExpressions[0].key=app.kubernetes.io/name \
  --set mcpServer.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.labelSelector.matchExpressions[0].operator=In \
  --set mcpServer.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.labelSelector.matchExpressions[0].values[0]=mcp-dbstore
```

## Configuration

### Common Configuration Options

#### Database Configuration

```yaml
# values.yaml
postgresql:
  auth:
    username: myuser
    password: mypassword
    database: mystore
  persistence:
    enabled: true
    size: 5Gi
    storageClass: "fast-ssd"
  resources:
    limits:
      memory: 1Gi
      cpu: 500m
```

#### MCP Server Configuration

```yaml
# values.yaml
mcpServer:
  replicaCount: 2
  image:
    tag: "latest"
  resources:
    limits:
      memory: 512Mi
      cpu: 500m
  env:
    MCP_SERVER_PORT: "8002"
    LOG_LEVEL: "INFO"
```

#### Security Configuration

```yaml
# values.yaml
mcpServer:
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    readOnlyRootFilesystem: true
  podSecurityContext:
    runAsNonRoot: true
    fsGroup: 1000
```

### Environment-Specific Values

Create environment-specific value files:

```bash
# Development environment
cat > values-dev.yaml << EOF
postgresql:
  persistence:
    size: 1Gi
mcpServer:
  replicaCount: 1
  resources:
    limits:
      memory: 256Mi
      cpu: 200m
EOF

# Production environment  
cat > values-prod.yaml << EOF
postgresql:
  persistence:
    size: 50Gi
    storageClass: "ssd"
  resources:
    limits:
      memory: 2Gi
      cpu: 1000m
mcpServer:
  replicaCount: 3
  resources:
    limits:
      memory: 1Gi
      cpu: 1000m
EOF

# Deploy with environment-specific values
helm install dev-inventory ./deploy/helm/mcp-dbstore -f values-dev.yaml
helm install prod-inventory ./deploy/helm/mcp-dbstore -f values-prod.yaml
```

## Usage

### Accessing the MCP Server

#### Internal Cluster Access

```bash
# Service name for internal cluster communication
SERVICE_NAME="mcp-dbstore-mcp-server.default.svc.cluster.local"
PORT="8002"

# Use from other pods in the cluster
curl http://${SERVICE_NAME}:${PORT}/health
```

#### External Access via Port Forward

```bash
# Port forward for local access
kubectl port-forward svc/mcp-dbstore-mcp-server 8002:8002

# Now accessible at http://localhost:8002
```

#### External Access via LoadBalancer

```bash
# Deploy with LoadBalancer service
helm upgrade mcp-dbstore ./deploy/helm/mcp-dbstore \
  --set mcpServer.service.type=LoadBalancer

# Get external IP
kubectl get svc mcp-dbstore-mcp-server
```

### Using the Tools

#### With MCP Inspector

```bash
# Install and run MCP inspector
pip install mcp-inspector
mcp-inspector http://localhost:8002

# Interactive tool exploration
# - Browse available tools
# - Test tool parameters
# - View tool responses
```

#### Programmatic Access

```python
import asyncio
import aiohttp

async def test_mcp_tools():
    base_url = "http://localhost:8002"
    
    # Get all products
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/tools/get_products",
            json={"skip": 0, "limit": 10}
        ) as response:
            products = await response.json()
            print(f"Found {len(products)} products")
    
    # Search for products
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/tools/search_products",
            json={"query": "widget", "limit": 5}
        ) as response:
            widgets = await response.json()
            print(f"Found {len(widgets)} widgets")

# Run the test
asyncio.run(test_mcp_tools())
```

### Database Access

#### Direct Database Connection

```bash
# Port forward PostgreSQL
kubectl port-forward svc/mcp-dbstore-postgresql 5432:5432 &

# Get database credentials
DB_USER=$(kubectl get secret mcp-dbstore-postgresql -o jsonpath="{.data.username}" | base64 --decode)
DB_PASS=$(kubectl get secret mcp-dbstore-postgresql -o jsonpath="{.data.password}" | base64 --decode)
DB_NAME=$(kubectl get secret mcp-dbstore-postgresql -o jsonpath="{.data.database}" | base64 --decode)

# Connect with psql
PGPASSWORD=$DB_PASS psql -h localhost -U $DB_USER -d $DB_NAME
```

#### Sample Queries

```sql
-- View all products
SELECT * FROM products ORDER BY name;

-- Check inventory levels
SELECT name, inventory FROM products WHERE inventory < 50;

-- View recent orders
SELECT o.id, p.name, o.quantity, o.customer_identifier 
FROM orders o 
JOIN products p ON o.product_id = p.id 
ORDER BY o.id DESC 
LIMIT 10;

-- Add custom product
INSERT INTO products (name, description, inventory, price) 
VALUES ('Custom Widget', 'A customized widget solution', 25, 149.99);
```

### Sample Data

The deployment includes 10 sample products:

- **Super Widget** ($29.99, 100 units)
- **Mega Gadget** ($79.50, 50 units)  
- **Awesome Gizmo** ($12.75, 200 units)
- **Hyper Doodad** ($45.00, 75 units)
- **Ultra Thingamajig** ($99.99, 120 units)
- **Quantum Sprocket** ($199.00, 30 units)
- **Stealth Frob** ($22.50, 150 units)
- **Cosmic Ratchet** ($65.20, 60 units)
- **Zenith Component** ($33.80, 90 units)
- **Nova Fastener** ($5.95, 250 units)

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=mcp-dbstore

# Check pod events
kubectl describe pod -l app.kubernetes.io/name=mcp-dbstore

# Common causes:
# - Insufficient resources
# - Image pull failures
# - Volume mount issues
```

#### 2. Database Connection Issues

```bash
# Check PostgreSQL pod logs
kubectl logs -f deployment/mcp-dbstore-postgresql

# Check MCP server init container
kubectl logs deployment/mcp-dbstore-mcp-server -c wait-for-db

# Test database connectivity
kubectl exec -it deployment/mcp-dbstore-postgresql -- pg_isready

# Verify secrets
kubectl get secret mcp-dbstore-postgresql -o yaml
kubectl get secret mcp-dbstore-mcp-server -o yaml
```

#### 3. MCP Server Connection Issues

```bash
# Check MCP server logs
kubectl logs -f deployment/mcp-dbstore-mcp-server

# Test port connectivity
kubectl port-forward svc/mcp-dbstore-mcp-server 8002:8002 &
curl http://localhost:8002/health

# Verify service endpoints
kubectl get endpoints mcp-dbstore-mcp-server
```

#### 4. Storage Issues

```bash
# Check PVC status
kubectl get pvc

# Check storage class
kubectl get storageclass

# Events related to storage
kubectl get events --field-selector reason=FailedMount
```

### Debug Mode

Enable detailed logging:

```bash
# Enable debug logging
helm upgrade mcp-dbstore ./deploy/helm/mcp-dbstore \
  --set mcpServer.env.LOG_LEVEL=DEBUG \
  --set mcpServer.env.PYTHONUNBUFFERED=1

# View detailed logs
kubectl logs -f deployment/mcp-dbstore-mcp-server
```

### Performance Issues

```bash
# Check resource usage
kubectl top pods -l app.kubernetes.io/name=mcp-dbstore

# Check resource limits
kubectl describe pod -l app.kubernetes.io/name=mcp-dbstore | grep -A5 Limits

# Scale if needed
kubectl scale deployment mcp-dbstore-mcp-server --replicas=3
```

### Recovery Procedures

#### Restart Services

```bash
# Restart MCP server
kubectl rollout restart deployment/mcp-dbstore-mcp-server

# Restart PostgreSQL (will cause brief downtime)
kubectl rollout restart deployment/mcp-dbstore-postgresql
```

#### Reset Database

```bash
# Delete and recreate PVC (DESTRUCTIVE)
kubectl delete pvc mcp-dbstore-postgresql-data
helm upgrade mcp-dbstore ./deploy/helm/mcp-dbstore
```

## Integration with Llama Stack

### Registering the MCP Server

```bash
# Register with Llama Stack
llamastack mcp-server register \
  --name inventory-management \
  --url http://mcp-dbstore-mcp-server.default.svc.cluster.local:8002 \
  --description "Product inventory management tools"

# Verify registration
llamastack mcp-server list

# Expected output:
# NAME                   URL                                              STATUS
# inventory-management   http://mcp-dbstore-mcp-server.default...         active
```

### Tool Discovery

When registered with Llama Stack, tools are automatically discovered:

```bash
# List discovered tools
llamastack tools list --mcp-server inventory-management

# Expected tools:
# - get_products
# - get_product_by_id  
# - get_product_by_name
# - search_products
# - add_product
# - remove_product
# - order_product
```

### Agent Configuration

```bash
# Create agent with inventory tools
llamastack agent create \
  --name inventory-agent \
  --description "AI agent for product inventory management" \
  --tool-groups inventory-management \
  --model llama-3-8b-instruct

# Test agent with inventory queries
llamastack agent chat inventory-agent \
  --message "Show me all products with low inventory (less than 50 units)"
```

### Toolgroup Usage

The MCP server appears as a single toolgroup in Llama Stack:

```yaml
# Agent configuration
agents:
  - name: inventory-manager
    model: llama-3-8b-instruct
    tool_groups:
      - inventory-management  # All 7 tools available
    system_prompt: |
      You are an inventory management assistant. You can help users:
      - Browse product catalogs
      - Search for specific products
      - Check inventory levels
      - Process orders
      - Add new products
      Use the available tools to provide accurate, up-to-date information.
```

## Monitoring

### Health Checks

```bash
# Pod health status
kubectl get pods -l app.kubernetes.io/name=mcp-dbstore

# Service endpoint health
kubectl get endpoints

# Application health (if health endpoint exists)
curl http://localhost:8002/health
```

### Logs

```bash
# MCP server logs
kubectl logs -f deployment/mcp-dbstore-mcp-server

# PostgreSQL logs
kubectl logs -f deployment/mcp-dbstore-postgresql

# All pods logs
kubectl logs -f -l app.kubernetes.io/name=mcp-dbstore
```

### Metrics (if enabled)

```bash
# View resource usage
kubectl top pods -l app.kubernetes.io/name=mcp-dbstore

# Custom metrics (requires monitoring stack)
kubectl get servicemonitor mcp-dbstore
```

### Alerts

Set up basic alerts for production:

```yaml
# PrometheusRule example
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: mcp-dbstore-alerts
spec:
  groups:
  - name: mcp-dbstore
    rules:
    - alert: MCPServerDown
      expr: up{job="mcp-dbstore-mcp-server"} == 0
      for: 1m
      annotations:
        summary: "MCP DBStore server is down"
    - alert: PostgreSQLDown
      expr: up{job="mcp-dbstore-postgresql"} == 0
      for: 1m
      annotations:
        summary: "PostgreSQL database is down"
```

### Backup and Recovery

```bash
# Database backup
kubectl exec -it deployment/mcp-dbstore-postgresql -- pg_dumpall -U mcpuser > backup.sql

# Restore from backup
kubectl exec -i deployment/mcp-dbstore-postgresql -- psql -U mcpuser < backup.sql
```

---

## Getting Help

- **Documentation**: [MCP DBStore Developer Guide](./mcp-dbstore-developer-guide.md)
- **Issues**: https://github.com/yourusername/ai-virtual-assistant/issues
- **MCP Protocol**: https://modelcontextprotocol.io/docs/
- **FastMCP**: https://github.com/jlowin/fastmcp
- **Helm Charts**: https://helm.sh/docs/

## Next Steps

1. **Explore Tools**: Use MCP inspector to understand available tools
2. **Integrate with Agents**: Register with Llama Stack for agent usage
3. **Customize Data**: Replace sample data with your actual inventory
4. **Scale Up**: Configure for production workloads
5. **Monitor**: Set up monitoring and alerting
6. **Extend**: Build additional MCP servers for other domains 