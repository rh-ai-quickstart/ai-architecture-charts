# Oracle SQLcl MCP Server

## 🚀 Overview

The Oracle SQLcl MCP Server enables AI agents to interact with Oracle databases through natural language queries. This server implements the Model Context Protocol (MCP) to provide database connectivity and SQL execution capabilities for AI-powered applications.

## ✅ Current Status

**FULLY OPERATIONAL** - The Oracle MCP server is working correctly with verified data flow from AI Virtual Agent → LlamaStack → Toolhive Proxy → Oracle MCP Server → Oracle Database.

**Verified Components**:
- ✅ Toolhive Operator v0.4.0 (resolves SSE channel management issues)
- ✅ Oracle 23ai database with TPC-DS data (100,000+ customer records)
- ✅ Oracle MCP server with named connection (`oracle_connection`)
- ✅ AI Virtual Agent integration with proper authentication
- ✅ Chat functionality working for appropriate query sizes

**Important Limitation**: Large datasets (e.g., "show me all customers") will exceed the LLM's context limit (32,768 tokens). Use pagination, limits, or aggregation queries instead.

## 📋 Prerequisites

### Required Components
- **Toolhive Operator**: v0.4.0 minimum (operator application version)
  - **For OpenShift**: Must use the official OpenShift-specific values file: [values-openshift.yaml](https://raw.githubusercontent.com/stacklok/toolhive/c7ef74ab08388f5c5add962d5e20e04da9c518c6/deploy/charts/operator/values-openshift.yaml)
- **Oracle Database**: Oracle 23ai deployed via oracle23ai Helm chart
- **Oracle Secret**: `oracle23ai` secret created by the oracle23ai Helm chart
- **Kubernetes Cluster**: OpenShift or standard Kubernetes
- **Storage Class**: `gp3-csi` or compatible storage class

### Installing Toolhive Operator

#### Step 1: Add Helm Repository
```bash
helm repo add toolhive https://stacklok.github.io/toolhive
helm repo update
```

#### Step 2: Install CRDs First
```bash
helm install toolhive-operator-crds toolhive/toolhive-operator-crds \
  --namespace toolhive-system \
  --create-namespace \
  --version 0.0.42 \
  --wait
```

#### Step 3: Install Operator with v0.4.0 Images
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
helm install toolhive-operator toolhive/toolhive-operator \
  --namespace toolhive-system \
  --version 0.3.0 \
  --values https://raw.githubusercontent.com/stacklok/toolhive/c7ef74ab08388f5c5add962d5e20e04da9c518c6/deploy/charts/operator/values-openshift.yaml \
  --values /tmp/toolhive-install.yaml \
  --wait
```

#### Step 4: Verify Installation
```bash
kubectl get pods -n toolhive-system
kubectl get pod -l app.kubernetes.io/name=toolhive-operator -n toolhive-system -o jsonpath='{.items[0].spec.containers[0].image}'
```

## 🚀 Deployment of AI-Virtual-Agent with Oracle MCP Server

### Quick Start

1. **Set Environment Variables**:
   ```bash
   export ADMIN_USERNAME=your-admin
   export ADMIN_EMAIL=your-email@company.com
   export HF_TOKEN=your-huggingface-token
   export NAMESPACE=your-namespace
   export ORACLE=true  # Required for Oracle-specific components
   ```

2. **Enable Oracle MCP Server**:
   ```yaml
   # In mcp-servers/helm/values.yaml
   mcp-servers:
     oracle-sqlcl:
       enabled: true  # Must be enabled before deployment
   ```

3. **Deploy**:
   ```bash
   cd ai-virtual-agent/deploy/cluster
   make install NAMESPACE=$NAMESPACE ORACLE=true
   ```

### Important Notes

- **Oracle Database First**: The oracle23ai database must be deployed before the MCP server
- **Oracle Secret Required**: The `oracle23ai` secret is automatically created by the oracle23ai Helm chart
- **MCP Server Not Default**: The oracle-sqlcl MCP server is **disabled by default** and must be explicitly enabled
- **ORACLE=true Required**: Without this environment variable, Oracle-specific components will not be installed

## 🔧 Configuration

### MCP Server Image Details
The Oracle MCP server uses the `quay.io/rh-ai-quickstart/oracle-sqlcl` image which includes:
- **Oracle SQLcl**: Command-line interface for Oracle databases
- **MCP Server Implementation**: Model Context Protocol server for AI integration
- **Startup Script**: Automatically creates named connections during pod initialization

### Named Connections
The Oracle MCP server automatically creates named connections during startup:

- **Connection Name**: `oracle_connection` (configurable via `ORACLE_CONN_NAME`)
- **User**: `system` (configurable via `ORACLE_USER`)
- **Connection String**: Extracted from `ORACLE_CONNECTION_STRING` environment variable
- **Password**: Stored securely using `-savepwd` flag

#### Managing Named Connections
```bash
# List all named connections
kubectl exec oracle-sqlcl-0 -c mcp -- /opt/oracle/sqlcl/bin/sql /NOLOG -c "connmgr list"

# Show connection details
kubectl exec oracle-sqlcl-0 -c mcp -- /opt/oracle/sqlcl/bin/sql /NOLOG -c "connmgr show oracle_connection"

# Test connection
kubectl exec oracle-sqlcl-0 -c mcp -- /opt/oracle/sqlcl/bin/sql /NOLOG -c "connect oracle_connection"
```

## 💡 Query Best Practices

### Recommended Query Patterns

**✅ Good Queries** (Will work well):
```sql
-- Pagination
"Show me the first 10 customers"
"List the top 50 customers by income"

-- Aggregation
"How many customers are there?"
"What's the average income of customers?"
"Show me customer statistics by state"

-- Filtered queries
"Show me customers from California"
"List customers with income above $50,000"
```

**❌ Avoid These Queries** (Will exceed context limit):
```sql
-- Large datasets
"Show me all customers"           -- 100,000+ rows
"List every customer record"      -- Too much data
"Display the entire customer table" -- Exceeds 32K token limit
```

### Context Limit Guidelines
- **LLM Context Limit**: 32,768 tokens
- **Typical Customer Record**: ~70-80 tokens
- **Safe Query Size**: ≤ 400 rows (≈ 32,000 tokens)
- **Recommended Limit**: ≤ 100 rows for optimal performance

### Query Optimization Tips
1. **Use ROWNUM**: `WHERE ROWNUM <= 10`
2. **Select Specific Columns**: Avoid `SELECT *`
3. **Add Filters**: Reduce result set size
4. **Use Aggregation**: `COUNT()`, `SUM()`, `AVG()` instead of raw data
5. **Implement Pagination**: Process data in chunks

## 🧪 Testing

### 1. Verify Deployment
```bash
# Check MCP server pod
kubectl get pods -l app.kubernetes.io/name=oracle-sqlcl

# Check MCPServer resource
kubectl get mcpserver oracle-sqlcl
```

### 2. Test Database Connection
```bash
# Check pod logs for connection status
kubectl logs oracle-sqlcl-0 -c mcp

# Test saved connection
kubectl exec oracle-sqlcl-0 -c mcp -- /opt/oracle/sqlcl/bin/sql /NOLOG -c "connmgr show oracle_connection"
```

### 3. Test AI Integration
1. **Access AI Virtual Agent**: Navigate to the application URL
2. **Select Oracle Agent**: Choose the Oracle MCP agent template
3. **Test Query**: Ask "Show me the first 10 customers" or "How many customers are there?"
4. **Verify Response**: Check that SQL is generated and executed

**⚠️ Important**: Avoid queries that return large datasets as they will exceed the LLM's context limit (32,768 tokens).

## 🔍 Troubleshooting

### Common Issues

#### 1. Toolhive Operator Not Installed
```bash
# Check if Toolhive operator is running
kubectl get pods -n toolhive-system

# If not installed, follow the installation process above
```

#### 2. Channel Full Error (SSE Proxy Issues)
If you encounter "Failed to send pending message to client (channel full)" errors:

**Root Cause**: Versions prior to v0.4.0 have SSE channel management issues.

**Solution**: Upgrade to v0.4.0:
```bash
# Create upgrade values file with v0.4.0 images
# Note: v0.4.0 refers to the Toolhive operator application version (not Helm chart version)
cat > /tmp/toolhive-upgrade.yaml << 'EOF'
operator:
  image: ghcr.io/stacklok/toolhive/operator:v0.4.0  # Toolhive operator app version
  toolhiveRunnerImage: ghcr.io/stacklok/toolhive/proxyrunner:v0.4.0  # Toolhive runner app version
EOF

# Upgrade with OpenShift-specific configuration
# Note: --version 0.3.0 is the Helm chart version (different from app version)
# The values-openshift.yaml file is required for OpenShift deployments
helm upgrade toolhive-operator toolhive/toolhive-operator \
  --namespace toolhive-system \
  --version 0.3.0 \
  --values https://raw.githubusercontent.com/stacklok/toolhive/c7ef74ab08388f5c5add962d5e20e04da9c518c6/deploy/charts/operator/values-openshift.yaml \
  --values /tmp/toolhive-upgrade.yaml \
  --wait

# Restart MCP server pods to pick up new proxy version
kubectl delete pod -l app.kubernetes.io/name=oracle-sqlcl
```

#### 3. OpenShift Security Context Constraint (SCC) Issues
If you encounter "unable to validate against any security context constraint" errors:

**Solution**: Use the OpenShift-specific values file which handles SCC requirements (see installation steps above).

#### 4. LLM Context Limit Exceeded
If you encounter errors like "This model's maximum context length is 32768 tokens":

**Root Cause**: The Oracle MCP server successfully executed your query, but the response exceeded the LLM's context limit.

**Solutions**:
```sql
-- Instead of: SELECT * FROM CUSTOMER
-- Use pagination:
SELECT * FROM CUSTOMER WHERE ROWNUM <= 10;

-- Use aggregation:
SELECT COUNT(*) FROM CUSTOMER;

-- Use filtering:
SELECT * FROM CUSTOMER WHERE AGE > 50 AND ROWNUM <= 100;
```

#### 5. MCP Server Not Starting
```bash
# Check pod logs
kubectl logs oracle-sqlcl-0 -c mcp

# Check init container logs
kubectl logs oracle-sqlcl-0 -c wait-for-oracle23ai
kubectl logs oracle-sqlcl-0 -c wait-for-oracle23ai-tpcds-populate
```

#### 6. Database Connection Failed
- **Verify Oracle secret exists**: `kubectl get secret oracle23ai`
- **Check connection string**: `kubectl get secret oracle23ai -o yaml`
- **Validate Oracle database**: Ensure database is accessible
- **Check SYSTEM account**: Ensure it's unlocked and password is correct

#### 7. Named Connection Issues
```bash
# Check if named connection was created during startup
kubectl exec oracle-sqlcl-0 -c mcp -- ls -la /sqlcl-home/.sqlcl/
kubectl exec oracle-sqlcl-0 -c mcp -- cat /sqlcl-home/.sqlcl/aliases.xml

# Manually create connection if startup failed
kubectl exec oracle-sqlcl-0 -c mcp -- /opt/oracle/sqlcl/bin/sql /NOLOG -c "connect -savepwd -save oracle_connection system/password@host:port/service"
```

### Debug Commands

```bash
# Get detailed pod information
kubectl describe pod oracle-sqlcl-0

# Check MCP server status
kubectl get mcpserver oracle-sqlcl -o yaml

# View toolhive operator logs
kubectl logs -l app.kubernetes.io/name=toolhive-operator -n toolhive-system

# Check Oracle database connectivity
kubectl exec oracle-sqlcl-0 -c mcp -- /opt/oracle/sqlcl/bin/sql /NOLOG -c "connect oracle_connection"
```

## 📚 References

- [Oracle SQLcl MCP Server Documentation](https://docs.oracle.com/en/database/oracle/sql-developer-command-line/25.2/sqcug/using-oracle-sqlcl-mcp-server.html)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Toolhive Operator Documentation](https://github.com/stacklok/toolhive)
- [Toolhive Operator v0.4.0 Release Notes](https://github.com/stacklok/toolhive/releases/tag/v0.4.0)

## 🎯 Quick Summary

### ✅ What's Working
- **Oracle MCP Server**: Fully operational with Toolhive Operator v0.4.0
- **Database Connectivity**: Oracle 23ai with 100,000+ customer records
- **AI Integration**: Chat functionality working for appropriate query sizes
- **Authentication**: Proper service account and RBAC configuration

### ⚠️ Key Limitations
- **Context Limit**: LLM can only handle ~32,768 tokens (≈ 400 rows)
- **Large Datasets**: Avoid queries like "show me all customers"
- **Query Size**: Use pagination, limits, or aggregation for large tables

### 🚀 Quick Start
1. **Install Toolhive Operator v0.4.0** (see Prerequisites section)
2. **Deploy Oracle 23ai database**
3. **Enable Oracle MCP server** (`oracle-sqlcl.enabled: true`)
4. **Set `ORACLE=true` environment variable**
5. **Run `make install NAMESPACE=$NAMESPACE ORACLE=true`**

### 💡 Best Practices
- Use `ROWNUM <= 10` for pagination
- Prefer aggregation queries (`COUNT`, `SUM`, `AVG`)
- Select specific columns instead of `SELECT *`
- Test with small datasets first

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../LICENSE) file for details.