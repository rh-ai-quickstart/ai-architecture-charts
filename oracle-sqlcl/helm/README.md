# Oracle SQLcl MCP Server Helm Chart

Note: Run these commands from the repository root (ai-architecture-charts). If you run them from another directory, adjust the chart path accordingly.

This chart deploys an Oracle SQLcl-based MCP server compatible with Toolhive. By default, it will also install Toolhive Operator CRDs and the Toolhive Operator as chart dependencies unless disabled via values.

**OpenShift Requirements**: This chart is designed for OpenShift and requires the `anyuid` Security Context Constraint (SCC) to be applied to the `toolhive-operator` service account for proper operation.

## Installation

### For OpenShift

```bash
# 1. Install the chart
helm upgrade --install oracle-sqlcl ./oracle-sqlcl/helm -n toolhive-oracle-mcp --create-namespace \
  --dependency-update \
  --set image.repository=quay.io/ecosystem-appeng/oracle-sqlcl

# 2. Apply the required SCC (Security Context Constraint)
oc adm policy add-scc-to-user anyuid -z toolhive-operator -n toolhive-oracle-mcp
```

### For other Kubernetes distributions

```bash
helm upgrade --install oracle-sqlcl ./oracle-sqlcl/helm -n toolhive-oracle-mcp --create-namespace \
  --dependency-update \
  --set image.repository=quay.io/ecosystem-appeng/oracle-sqlcl
```

Note: `image.tag` is optional. If omitted, the chart defaults to the chart `appVersion` defined in `Chart.yaml`. To override, pass `--set image.tag=<tag>`.

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

### Dependencies
This chart declares the following dependencies (fetched when using `--dependency-update` or after running `helm dependency build`):

- `toolhive-operator-crds` (repo: `https://stacklok.github.io/toolhive`, version: `0.0.24`)
- `toolhive-operator` (repo: `https://stacklok.github.io/toolhive`, version: `0.2.12`)

You can disable either via values:

```bash
helm upgrade --install oracle-sqlcl ./oracle-sqlcl/helm -n toolhive-oracle-mcp \
  --dependency-update \
  --set toolhiveOperatorCrds.enabled=false \
  --set toolhiveOperator.enabled=false
```

## Values
- `image.repository`, `image.pullPolicy` (optional `image.tag` defaults to chart `appVersion`)
- `permissionProfile.name`, `permissionProfile.type`
- `serviceAccount.create`, `serviceAccount.name`
- `persistence.data.*`
- `env.*` (used for Secret when `secret.enabled=true`)
- `rbac.scc.enabled`, `rbac.scc.name`
- `toolhiveOperatorCrds.enabled`, `toolhiveOperator.enabled`

## Uninstall
```bash
helm uninstall oracle-sqlcl -n toolhive-oracle-mcp 
```
