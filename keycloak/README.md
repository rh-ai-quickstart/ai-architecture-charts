# Keycloak Helm Chart

Official Keycloak Helm chart for identity and access management.

## Overview

This Helm chart deploys Keycloak using the official Keycloak container images from `quay.io/keycloak/keycloak`. It supports:

- Official Keycloak images (not Bitnami)
- External database configuration (PostgreSQL, MySQL, MariaDB)
- OpenShift Routes and Kubernetes Ingress
- Production-optimized deployment
- Flexible configuration via environment variables

## Prerequisites

- Kubernetes 1.23+ or OpenShift 4.10+
- Helm 3.0+
- **No external database required** - This chart includes a pgvector PostgreSQL subchart
- For external database: PostgreSQL, MySQL, or MariaDB

## Installation

### Standalone Installation (with built-in pgvector database)

```bash
# Create namespace
kubectl create namespace keycloak

# Install chart with built-in pgvector PostgreSQL
helm install keycloak ./keycloak/helm \
  --namespace keycloak \
  --set admin.password=changeme \
  --set pgvector.secret.password=changeme
```

### Standalone Installation (with external database)

```bash
# Install chart with external database
helm install keycloak ./keycloak/helm \
  --namespace keycloak \
  --set admin.password=changeme \
  --set pgvector.externalDatabase.enabled=true \
  --set pgvector.externalDatabase.host=postgresql.default.svc.cluster.local \
  --set pgvector.externalDatabase.port=5432 \
  --set pgvector.externalDatabase.user=keycloak \
  --set pgvector.externalDatabase.password=changeme \
  --set pgvector.externalDatabase.dbname=keycloak
```

### As Subchart (Used in other projects)

This chart can be used as a dependency in other Helm charts:

```yaml
# Chart.yaml for your application
dependencies:
  - name: keycloak
    version: "1.0.0"
    repository: "file://../ai-architecture-charts/keycloak/helm"
    # Or from Helm repository:
    # repository: "https://rh-ai-quickstart.github.io/ai-architecture-charts"
```

```bash
helm dependency update
helm install my-app . --namespace my-namespace
```

## Configuration

### Required Values

```yaml
admin:
  password: "your-admin-password"  # Or use existingSecret

# For built-in pgvector database (default):
pgvector:
  enabled: true
  secret:
    host: "pgvector"  # Auto-configured
    password: "your-db-password"

# For external database:
pgvector:
  externalDatabase:
    enabled: true
    host: "postgresql.default.svc.cluster.local"
    port: "5432"
    user: "keycloak"
    password: "your-db-password"
    dbname: "keycloak"
```

### Common Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicas` | Number of Keycloak replicas | `1` |
| `image.registry` | Image registry | `quay.io` |
| `image.repository` | Image repository | `keycloak/keycloak` |
| `image.tag` | Image version | `26.0.7` |
| `admin.username` | Admin username | `admin` |
| `admin.password` | Admin password | `""` (required) |
| `admin.existingSecret` | Existing secret for admin password | `""` |
| `database.vendor` | Database type | `postgres` |
| `pgvector.enabled` | Enable built-in PostgreSQL | `true` |
| `pgvector.secret.host` | Database hostname | `pgvector` |
| `pgvector.secret.port` | Database port | `5432` |
| `pgvector.secret.user` | Database username | `keycloak` |
| `pgvector.secret.password` | Database password | `""` (required) |
| `pgvector.secret.dbname` | Database name | `keycloak` |
| `config.hostname` | External URL (include `https://`) | `""` |
| `config.proxyHeaders` | Proxy header mode | `xforwarded` |
| `route.enabled` | Enable OpenShift Route | `true` |
| `ingress.enabled` | Enable Kubernetes Ingress | `false` |

For all available options, see `values.yaml`.

## Examples

### Using Existing Secrets (Recommended for Production)

```yaml
admin:
  existingSecret: "keycloak-admin-secret"
  existingSecretKey: "password"

# For external database, use pgvector.externalDatabase
pgvector:
  externalDatabase:
    enabled: true
    host: "postgresql.example.com"
    port: "5432"
    user: "keycloak"
    password: "your-db-password"  # Set via --set flag
    dbname: "keycloak"
```

```bash
# Create admin secret
kubectl create secret generic keycloak-admin-secret \
  --from-literal=password='your-admin-password'

# Install chart (database credentials via --set)
helm install keycloak ./keycloak/helm \
  --set pgvector.externalDatabase.enabled=true \
  --set pgvector.externalDatabase.host='postgresql.example.com' \
  --set pgvector.externalDatabase.password='your-db-password'
```

### OpenShift with Custom Route

```yaml
route:
  enabled: true
  host: "keycloak.apps.example.com"
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
```

### Kubernetes with Ingress

```yaml
route:
  enabled: false

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: keycloak.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: keycloak-tls
      hosts:
        - keycloak.example.com
```

### High Availability Setup

> **Important:** Multi-replica deployments require Infinispan cache discovery
> configuration so that Keycloak pods can form a cluster. Without it, each
> replica runs an isolated cache and users will experience session
> inconsistency (e.g., authenticated on pod A but getting a 401 on pod B).
> The example below uses DNS_PING discovery via a headless Service that you
> must create separately.

```yaml
replicas: 3

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

podDisruptionBudget:
  enabled: true
  minAvailable: 2

# Required for clustering — configure Infinispan discovery
extraEnv:
  - name: KC_CACHE_STACK
    value: "kubernetes"
  - name: JAVA_OPTS_APPEND
    value: "-Djgroups.dns.query=keycloak-headless"
```

### Custom Features

```yaml
config:
  features: "token-exchange,admin-fine-grained-authz"
  logLevel: "DEBUG"

extraEnv:
  - name: KC_SPI_THEME_DEFAULT
    value: "custom"
  - name: KC_DB_POOL_MAX_SIZE
    value: "20"
```

## Database Setup

### Built-in pgvector PostgreSQL (Default)

By default, this chart deploys a dedicated **pgvector PostgreSQL instance** for Keycloak. No external database setup is required!

**Automatic setup includes:**
- ✅ PostgreSQL with pgvector extension
- ✅ Dedicated database for Keycloak
- ✅ Automatic user and permissions setup
- ✅ Persistent volume for data

**Configuration:**
```yaml
pgvector:
  enabled: true  # Default
  secret:
    user: keycloak
    password: changeme  # Change for production!
    dbname: keycloak
    port: "5432"
```

### External Database (Optional)

If you prefer to use an existing PostgreSQL instance, enable `externalDatabase`. The pgvector subchart will skip the StatefulSet and Service, and create only a Secret and init Job pointing to the external database.

**Configuration:**
```yaml
pgvector:
  externalDatabase:
    enabled: true
    host: postgresql.example.com
    port: "5432"
    user: keycloak
    password: your-password  # Set via --set flag
    dbname: keycloak
```

**Note:** When `externalDatabase` is enabled, the `pgvector.secret.*` fields are ignored.

**PostgreSQL Setup Example:**

```sql
CREATE DATABASE keycloak;
CREATE USER keycloak WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;

-- Connect to keycloak database
\c keycloak

GRANT ALL ON SCHEMA public TO keycloak;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO keycloak;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO keycloak;
```

## Upgrading

### Upgrade Keycloak Version

```bash
# Update values.yaml or use --set
helm upgrade keycloak ./keycloak/helm \
  --set image.tag=26.1.0 \
  --reuse-values
```

### Upgrade Chart

```bash
helm upgrade keycloak ./keycloak/helm \
  --namespace keycloak
```

## Uninstallation

```bash
helm uninstall keycloak --namespace keycloak
```

**Note:** This does not delete the database. Database cleanup must be done manually.

## Troubleshooting

### OpenID Configuration Shows localhost:8080 URLs

**Problem:** The OpenID configuration endpoint returns URLs with `localhost:8080` instead of the external URL.

**Cause:** Keycloak doesn't know its external hostname.

**Solution:** Set `config.hostname` to the full external URL (including `https://`):

```bash
helm upgrade keycloak ./keycloak/helm \
  --set config.hostname=https://keycloak-myapp.apps.example.com
```

**Verify the fix:**
```bash
# Check if KC_HOSTNAME is set in the deployment
oc get deployment keycloak -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="KC_HOSTNAME")].value}'

# Test the OpenID configuration
curl https://your-keycloak-url/realms/your-realm/.well-known/openid-configuration | jq .issuer
```

### Pod Fails to Start

Check logs:
```bash
kubectl logs -l app.kubernetes.io/name=keycloak --tail=100
```

Common issues:
- Database connection failed (check host, credentials)
- Missing admin password
- Insufficient resources

### Database Connection Errors

Verify database connectivity:
```bash
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h postgresql -U keycloak -d keycloak
```

### Access Admin Console

Get the URL:
```bash
# OpenShift Route
oc get route keycloak -o jsonpath='{.spec.host}'

# Kubernetes Ingress
kubectl get ingress keycloak -o jsonpath='{.spec.rules[0].host}'

# Port forward
kubectl port-forward svc/keycloak 8080:8080
# Access: http://localhost:8080
```

## Health Checks

Keycloak provides health endpoints:

- **Liveness**: `GET /health/live`
- **Readiness**: `GET /health/ready`
- **Metrics**: `GET /metrics` (if enabled)

## Security

### Production Checklist

- [ ] Use strong admin password
- [ ] Use strong database password
- [ ] Store passwords in Kubernetes Secrets
- [ ] Enable TLS (via Route/Ingress)
- [ ] Configure proper resource limits
- [ ] Enable Pod Security Policies
- [ ] Regular backups of database

### RBAC

The chart creates a ServiceAccount with minimal permissions. For additional permissions, create a RoleBinding:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: keycloak-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: admin
subjects:
- kind: ServiceAccount
  name: keycloak
  namespace: keycloak
```

## Development

### Local Testing

```bash
# Lint chart
helm lint ./keycloak/helm

# Render templates (with built-in database)
helm template keycloak ./keycloak/helm \
  --set admin.password=test \
  --set pgvector.secret.password=test

# Render templates (with external database)
helm template keycloak ./keycloak/helm \
  --set admin.password=test \
  --set pgvector.externalDatabase.enabled=true \
  --set pgvector.externalDatabase.host=postgresql \
  --set pgvector.externalDatabase.user=keycloak \
  --set pgvector.externalDatabase.password=test \
  --set pgvector.externalDatabase.dbname=keycloak

# Dry run
helm install keycloak ./keycloak/helm \
  --dry-run --debug \
  --set admin.password=test \
  --set pgvector.secret.password=test
```

### Package Chart

```bash
helm package ./keycloak/helm
```

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak Container Guide](https://www.keycloak.org/server/containers)
- [Keycloak Configuration](https://www.keycloak.org/server/all-config)
- [Official Keycloak Images](https://quay.io/repository/keycloak/keycloak)

## License

This chart is provided as-is.

## Support

For issues and questions:
- File an issue in the project repository
- Check Keycloak community forums
- Consult Keycloak documentation

