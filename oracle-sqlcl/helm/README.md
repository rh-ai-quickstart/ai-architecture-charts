# Oracle SQLcl MCP Server Helm Chart

Note: Run these commands from the repository root (ai-architecture-charts). If you run them from another directory, adjust the chart path accordingly.

This chart deploys an Oracle SQLcl-based MCP server compatible with Toolhive. It assumes Toolhive and related CRDs are already installed in the cluster.

## Installation

```bash
helm upgrade --install oracle-sqlcl ./oracle-sqlcl/helm -n toolhive-oracle-mcp --create-namespace \
  --set image.repository=quay.io/ecosystem-appeng/oracle-sqlcl-mcp-server \
  --set image.tag=1.0.0
```

### Provide Oracle connection via Secret (recommended)

```bash
helm upgrade --install oracle-sqlcl ./oracle-sqlcl/helm -n toolhive-oracle-mcp \
  --set secret.enabled=true \
  --set env.ORACLE_USER=sales \
  --set env.ORACLE_PASSWORD=changeme \
  --set env.ORACLE_CONNECTION_STRING="jdbc:oracle:thin:@host:1521/SERVICE" \
  --set env.ORACLE_CONN_NAME=oracle_connection
```

### Storage
- Data PVC for SQLcl HOME: enabled by default (`persistence.data`)

### OpenShift SCC (optional)
Enable and bind SCC to the ServiceAccount:
```bash
helm upgrade --install oracle-sqlcl ./oracle-sqlcl/helm -n toolhive-oracle-mcp \
  --set rbac.scc.enabled=true \
  --set serviceAccount.create=true
```

## Values
- `image.repository`, `image.tag`, `image.pullPolicy`
- `permissionProfile.name`, `permissionProfile.type`
- `serviceAccount.create`, `serviceAccount.name`
- `persistence.data.*`
- `env.*` (used for Secret when `secret.enabled=true`)
- `rbac.scc.enabled`, `rbac.scc.name`

## Uninstall
```bash
helm uninstall oracle-sqlcl -n toolhive-oracle-mcp 
```
