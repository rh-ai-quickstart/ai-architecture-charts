# Keycloak Helm Chart

This Helm chart deploys Keycloak on OpenShift for authentication and identity management, providing SSO (Single Sign-On) capabilities for applications.

## Overview

The keycloak chart creates:
- A Keycloak deployment for identity and access management
- OpenShift Route for external access
- Secrets for admin credentials and database configuration
- Optional persistent volume claims for data storage
- Optional realm import via ConfigMap
- Health probes for container lifecycle management

## Prerequisites

- OpenShift cluster (4.x+)
- Helm 3.x
- oc CLI
- Optional: PostgreSQL database for production deployments

## Installation

### Basic Installation (Development Mode)

```bash
helm install keycloak ./helm -n keycloak --create-namespace
```

Uses `start-dev` with the built-in H2 database. Not recommended for production.

### Installation with Custom Admin Credentials

```bash
helm install keycloak ./helm \
  --namespace keycloak \
  --create-namespace \
  --set secret.adminUser=myadmin \
  --set secret.adminPassword=MySecurePassword123!
```

### Installation with External PostgreSQL

```bash
helm install keycloak ./helm \
  --namespace keycloak \
  --create-namespace \
  --set secret.dbEnabled=true \
  --set secret.dbUrl="jdbc:postgresql://postgres-host:5432/keycloak" \
  --set secret.dbUsername=keycloak \
  --set secret.dbPassword=your-db-password
```

### Installation with Custom Namespace

```bash
helm install keycloak ./helm \
  --namespace identity \
  --create-namespace
```

## Configuration

### Key Configuration Options

#### Keycloak Core Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `quay.io/keycloak/keycloak` |
| `image.tag` | Image tag | `25.0.6` |
| `args` | Startup arguments | `["start-dev", "--proxy-headers=xforwarded"]` |

#### Admin Credentials Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secret.adminUser` | Admin username | `admin` |
| `secret.adminPassword` | Admin password | `admin` |

#### Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secret.dbEnabled` | Enable external database | `false` |
| `secret.dbUrl` | JDBC database URL | `jdbc:postgresql://postgres:5432/keycloak` |
| `secret.dbUsername` | Database username | `keycloak` |
| `secret.dbPassword` | Database password | `keycloak` |

#### Route Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `route.enabled` | Create OpenShift route | `true` |
| `route.host` | Custom hostname for route | `""` (auto-generated) |

#### Persistence Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistent storage | `false` |
| `persistence.size` | PVC size | `1Gi` |

#### Resource Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `1Gi` |
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |

#### Realm Import Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `realmImport.enabled` | Enable realm import at startup | `true` |

When enabled, the chart loads `realm.json` from the chart directory into a ConfigMap, mounts it at `/opt/keycloak/data/import/`, and appends `--import-realm` to the startup args.

### Example values.yaml

#### Example 1: Development Mode (default)

```yaml
replicaCount: 1

args:
  - start-dev
  - --proxy-headers=xforwarded

secret:
  adminUser: admin
  adminPassword: admin
  dbEnabled: false

route:
  enabled: true

realmImport:
  enabled: true
```

#### Example 2: Production Mode with PostgreSQL

```yaml
replicaCount: 3

args:
  - start
  - --optimized
  - --http-enabled=true
  - --http-port=8080
  - --hostname-strict=false
  - --proxy-headers=xforwarded

secret:
  adminUser: keycloak-admin
  adminPassword: YourSecurePassword123!
  dbEnabled: true
  dbUrl: "jdbc:postgresql://postgres-host:5432/keycloak"
  dbUsername: keycloak
  dbPassword: your-secure-db-password

livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 120
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

persistence:
  enabled: true
  size: 5Gi

resources:
  requests:
    cpu: "1000m"
    memory: "2Gi"
  limits:
    cpu: "4000m"
    memory: "4Gi"
```

#### Example 3: Custom Realm Import

```yaml
replicaCount: 1

secret:
  adminUser: admin
  adminPassword: admin

realmImport:
  enabled: true

route:
  enabled: true
  host: keycloak.apps.example.com
```

Edit `helm/realm.json` to define your realm, clients, roles, and users. See the [Keycloak Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/#_export_import) for the full JSON schema.

## Usage

After installation, the chart will create:

1. **Keycloak Deployment**: A complete identity and access management server
2. **OpenShift Route**: External HTTPS access to the Keycloak console
3. **Secrets**: Admin credentials and optional database configuration
4. **ConfigMap** (optional): Realm import configuration
5. **PVC** (optional): Persistent storage for Keycloak data

### Development vs Production Mode

| Aspect | Development | Production |
|--------|-------------|------------|
| Command | `start-dev` | `start --optimized` |
| Database | H2 (in-memory) | PostgreSQL |
| Health Probe Port | 9000 | 8080 |
| Admin Credentials | admin/admin | Must be changed |
| Replicas | 1 | 2-3+ recommended |

### Accessing Keycloak

Get the route URL:

```bash
oc get route keycloak -n keycloak -o jsonpath='{.spec.host}'
```

Navigate to `https://<hostname>/admin` and login with your admin credentials.

Retrieve credentials from the secret:

```bash
oc get secret keycloak-admin -n keycloak -o jsonpath='{.data.admin-user}' | base64 -d
oc get secret keycloak-admin -n keycloak -o jsonpath='{.data.admin-password}' | base64 -d
```

### Realm Import

When `realmImport.enabled: true`:
- Keycloak imports the realm on first startup
- Keycloak skips importing a realm if it already exists
- Delete the realm via the admin console to re-import
- Set `temporary: true` on user credentials to force a password change on first login

## Monitoring and Troubleshooting

### Checking Pod Status

```bash
oc get pods -l app.kubernetes.io/name=keycloak -n keycloak
```

### Viewing Logs

```bash
oc logs -f deployment/keycloak -n keycloak
```

### Common Issues

1. **Pod won't start (CrashLoopBackOff)**:
   - Check if health probe ports match the startup mode (9000 for dev, 8080 for production)
   - Verify database connectivity if using external PostgreSQL
   - Check resource limits are sufficient

2. **Database connection issues**:
   - Verify PostgreSQL is running and accessible
   - Check JDBC URL format and credentials
   - Ensure network policies allow connectivity

3. **Route not accessible**:
   - Check route status: `oc get route keycloak -n keycloak`
   - Verify TLS configuration
   - Check router pods in openshift-ingress namespace

4. **Realm import not working**:
   - Verify `realm.json` exists in the helm directory
   - Check if realm already exists (import is skipped)
   - Review pod logs for import errors

5. **Health probe failures**:
   - In production mode (`start --optimized`), health probes must use port 8080
   - In development mode (`start-dev`), health probes use port 9000
   - Increase `initialDelaySeconds` if Keycloak needs more startup time

### Checking Configuration

```bash
# Check secrets
oc get secrets -l app.kubernetes.io/name=keycloak -n keycloak

# Check configmaps
oc get configmaps -l app.kubernetes.io/name=keycloak -n keycloak

# Check PVCs
oc get pvc -l app.kubernetes.io/name=keycloak -n keycloak

# Check route
oc get route keycloak -n keycloak
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade keycloak ./helm -n keycloak -f custom-values.yaml
```

## Uninstalling

```bash
helm uninstall keycloak -n keycloak
```

**Note**: This will not delete PVCs by default. To also remove persistent data:

```bash
oc delete pvc -l app.kubernetes.io/name=keycloak -n keycloak
```

## Dependencies

- **OpenShift cluster**: Required for Route resources and container platform
- **PostgreSQL** (production): External database for production deployments
- **Sufficient cluster resources**: CPU, memory, and storage
- **Container registry access**: For pulling Keycloak images from quay.io
- **Network connectivity**: Between Keycloak and database (if external)

## Integration

This chart works well with other components in the AI architecture:

- **llama-stack**: Secure LLM inference with Keycloak authentication
- **configure-pipeline**: Protect data science pipelines with SSO
- **pgvector**: Share PostgreSQL infrastructure for both Keycloak and vector storage
- **minio**: Secure object storage access with Keycloak policies

## Support

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak GitHub](https://github.com/keycloak/keycloak)
- [OpenShift Documentation](https://docs.openshift.com/)
