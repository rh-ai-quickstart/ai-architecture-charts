# Keycloak Helm Chart for OpenShift

Deploys Keycloak on OpenShift for authentication and identity management.

## Prerequisites

- OpenShift cluster (4.x+)
- Helm 3.x
- oc CLI
- Optional: PostgreSQL database for production

## Installation

### Development Mode

```bash
helm install keycloak ./helm -n keycloak --create-namespace
```

Uses `start-dev` with the built-in H2 database. Not recommended for production.

### Production Mode

Create a `production-values.yaml`:

You will need to have a postgres database to back this application.

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
  adminUser: your-admin-username
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
```

Install:

```bash
helm install keycloak ./helm -n keycloak --create-namespace -f production-values.yaml
```

**Note:** In production mode (`start --optimized`), health probes must use port 8080 instead of 9000.

## Configuration

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `quay.io/keycloak/keycloak` |
| `image.tag` | Image tag | `25.0.6` |
| `args` | Startup arguments | `["start-dev", "--proxy-headers=xforwarded"]` |
| `secret.adminUser` | Admin username | `admin` |
| `secret.adminPassword` | Admin password | `admin` |
| `secret.dbEnabled` | Enable external database | `false` |
| `secret.dbUrl` | JDBC database URL | `jdbc:postgresql://postgres:5432/keycloak` |
| `secret.dbUsername` | Database username | `keycloak` |
| `secret.dbPassword` | Database password | `keycloak` |
| `persistence.enabled` | Enable persistent storage | `false` |
| `persistence.size` | PVC size | `1Gi` |
| `route.enabled` | Create OpenShift route | `true` |
| `route.host` | Custom hostname for route | `""` (auto-generated) |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `1Gi` |
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |

### Realm Import

| Parameter | Description | Default |
|-----------|-------------|---------|
| `realmImport.enabled` | Enable realm import at startup | `true` |

When enabled, the chart loads `realm.json` from the chart directory into a ConfigMap, mounts it at `/opt/keycloak/data/import/`, and appends `--import-realm` to the startup args. Keycloak imports the realm on first startup.

Edit `helm/realm.json` to define your realm, clients, roles, and users. See the [Keycloak Server Administration Guide](https://www.keycloak.org/docs/latest/server_admin/#_export_import) for the full JSON schema.

**Notes:**
- Keycloak skips importing a realm if it already exists. Delete the realm via the admin console to re-import.
- Set `temporary: true` on user credentials to force a password change on first login.

## Accessing Keycloak

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

## Production Notes

| Aspect | Development | Production |
|--------|-------------|------------|
| Command | `start-dev` | `start --optimized` |
| Database | H2 (in-memory) | PostgreSQL |
| Health Probe Port | 9000 | 8080 |
| Admin Credentials | admin/admin | Must be changed |
| Replicas | 1 | 2-3+ recommended |

Key requirements:
- An external PostgreSQL database is required for production mode
- Health probes must target port 8080 (not 9000) in production
- Always change the default admin credentials
- Use strong passwords and consider External Secrets Operator for credential management

## Upgrading

```bash
helm upgrade keycloak ./helm -n keycloak -f custom-values.yaml
```

## Uninstalling

```bash
helm uninstall keycloak -n keycloak
```

Delete persistent volume claims:

```bash
oc delete pvc -l app.kubernetes.io/name=keycloak -n keycloak
```

## Troubleshooting

Check pod logs:

```bash
oc logs -f deployment/keycloak -n keycloak
```

Check pod events:

```bash
oc describe pod -l app.kubernetes.io/name=keycloak -n keycloak
```

Check route status:

```bash
oc get route keycloak -n keycloak
```

## Support

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak GitHub](https://github.com/keycloak/keycloak)
- [OpenShift Documentation](https://docs.openshift.com/)
