# Keycloak Helm Chart for OpenShift

This Helm chart deploys Keycloak on OpenShift with support for authentication and identity management.

## Overview

Keycloak is an open-source identity and access management solution that provides:
- Single Sign-On (SSO)
- Identity Brokering and Social Login
- User Federation
- Client Adapters
- Admin Console
- Account Management Console

## Prerequisites

- OpenShift cluster (4.x or later)
- Helm 3.x
- kubectl/oc CLI
- Optional: PostgreSQL database (recommended for production)

## Installation

### Development Mode (No External Database)

Deploy Keycloak in development mode with built-in H2 database:

```bash
helm install keycloak ./helm -n keycloak --create-namespace
```

This uses `start-dev` mode which:
- Uses built-in H2 database (data stored in-memory)
- Configured with `--proxy-headers=xforwarded` for OpenShift route compatibility
- Suitable for testing and development
- **Not recommended for production**

**Note**: The proxy headers configuration is essential for OpenShift routes with TLS termination to prevent mixed content errors.

### Production Mode (With External PostgreSQL Database)

For production deployments, use an external PostgreSQL database. Create a values file:

**production-values.yaml:**
```yaml
args:
  - start
  - --optimized
  - --http-enabled=true
  - --http-port=8080
  - --hostname-strict=false
  - --proxy-headers=xforwarded

secret:
  dbEnabled: true
  dbUrl: "jdbc:postgresql://postgres:5432/keycloak"
  dbUsername: keycloak
  dbPassword: changeme
```

Then install:
```bash
helm install keycloak ./helm -n keycloak --create-namespace -f production-values.yaml
```

### Custom Installation

Deploy with custom admin credentials:

```bash
helm install keycloak ./helm -n keycloak --create-namespace \
  --set secret.adminUser=myadmin \
  --set secret.adminPassword=mysecurepassword
```

### Using a Custom Values File (Production)

Create a `production-values.yaml` file:

```yaml
replicaCount: 2

image:
  tag: "25.0.6"

# Production mode args
args:
  - start
  - --optimized
  - --http-enabled=true
  - --http-port=8080
  - --hostname-strict=false
  - --proxy-headers=xforwarded

secret:
  adminUser: admin
  adminPassword: changeme
  dbEnabled: true
  dbUrl: "jdbc:postgresql://postgres:5432/keycloak"
  dbUsername: keycloak
  dbPassword: keycloak

resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

persistence:
  enabled: true
  size: 5Gi

route:
  enabled: true
  host: keycloak.apps.example.com
```

Install with custom values:

```bash
helm install keycloak ./helm -n keycloak -f production-values.yaml
```

## Configuration

### Key Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of Keycloak replicas | `1` |
| `image.repository` | Keycloak image repository | `quay.io/keycloak/keycloak` |
| `image.tag` | Keycloak image tag | `25.0.6` |
| `args` | Keycloak startup arguments | `["start-dev", ...]` (dev mode) |
| `secret.adminUser` | Admin username | `admin` |
| `secret.adminPassword` | Admin password | `admin` |
| `secret.dbEnabled` | Enable external database configuration | `false` |
| `secret.dbUrl` | JDBC database URL (when dbEnabled=true) | `jdbc:postgresql://postgres:5432/keycloak` |
| `secret.dbUsername` | Database username (when dbEnabled=true) | `keycloak` |
| `secret.dbPassword` | Database password (when dbEnabled=true) | `keycloak` |
| `persistence.enabled` | Enable persistent storage | `false` |
| `persistence.size` | PVC size | `1Gi` |
| `route.enabled` | Create OpenShift route | `true` |
| `route.host` | Custom hostname for route | `""` (auto-generated) |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `1Gi` |
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |

### Realm Import Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `realmImport.enabled` | Enable realm import at startup | `false` |
| `realmImport.realms` | List of realm configurations to import | `[]` |
| `realmImport.realms[].realm` | Realm name (required) | - |
| `realmImport.realms[].displayName` | Display name for the realm | realm name |
| `realmImport.realms[].clients` | List of OAuth/OIDC clients | `[]` |
| `realmImport.realms[].roles.realm` | List of realm-level roles | `[]` |
| `realmImport.realms[].users` | List of users with credentials and roles | `[]` |

### Advanced Configuration

For a complete list of configuration options, see the `values.yaml` file.

## Realm Import (Pre-configured Realms, Users, and Clients)

Keycloak supports importing realm configurations at startup using the `--import-realm` flag. This chart leverages that feature to let you define realms, clients, roles, and users entirely in your `values.yaml` -- **no separate Job or post-deploy script needed**.

### How It Works

When `realmImport.enabled: true`:
1. A ConfigMap is created for each realm containing the realm JSON configuration
2. The ConfigMaps are mounted into the Keycloak container at `/opt/keycloak/data/import/`
3. The `--import-realm` flag is automatically appended to the Keycloak startup args
4. Keycloak reads and imports the realm(s) during startup

### Example: Single Realm with Users and Clients

```yaml
realmImport:
  enabled: true
  realms:
    - realm: "my-app"
      enabled: true
      displayName: "My Application"
      ssoSessionIdleTimeout: 1800
      accessTokenLifespan: 300
      clients:
        - clientId: "frontend-app"
          enabled: true
          publicClient: true
          directAccessGrantsEnabled: true
          redirectUris:
            - "https://my-app.example.com/*"
          webOrigins:
            - "https://my-app.example.com"
          protocol: "openid-connect"
          standardFlowEnabled: true
        - clientId: "backend-service"
          enabled: true
          publicClient: false
          clientAuthenticatorType: "client-secret"
          secret: "change-me-in-production"
          serviceAccountsEnabled: true
          protocol: "openid-connect"
      roles:
        realm:
          - name: "admin"
            description: "Administrator role"
          - name: "user"
            description: "Regular user role"
      users:
        - username: "admin-user"
          enabled: true
          emailVerified: true
          firstName: "Admin"
          lastName: "User"
          email: "admin@example.com"
          credentials:
            - type: "password"
              value: "change-me"
              temporary: true
          realmRoles:
            - "admin"
            - "user"
        - username: "test-user"
          enabled: true
          firstName: "Test"
          lastName: "User"
          email: "test@example.com"
          credentials:
            - type: "password"
              value: "testpassword"
              temporary: false
          realmRoles:
            - "user"
```

### Example: Multiple Realms

You can define multiple realms -- each gets its own ConfigMap:

```yaml
realmImport:
  enabled: true
  realms:
    - realm: "internal"
      enabled: true
      displayName: "Internal Applications"
      clients:
        - clientId: "intranet"
          enabled: true
          publicClient: true
          redirectUris: ["https://intranet.example.com/*"]
      users:
        - username: "employee1"
          enabled: true
          credentials:
            - type: "password"
              value: "welcome123"
              temporary: true
          realmRoles: ["user"]
    - realm: "external"
      enabled: true
      displayName: "External Partners"
      clients:
        - clientId: "partner-portal"
          enabled: true
          publicClient: true
          redirectUris: ["https://partners.example.com/*"]
```

### Important Notes

- **Import behavior**: Keycloak will **skip** importing a realm if it already exists. It does **not** overwrite existing realms. To re-import, delete the realm first via the admin console.
- **Temporary passwords**: Set `temporary: true` on user credentials to force a password change on first login (recommended for production).
- **Client secrets**: For confidential clients, set `publicClient: false` and provide a `secret`. Rotate these in production.
- **Startup time**: Importing large realm configurations may increase initial startup time slightly.

## Accessing Keycloak

### Get the Route URL

```bash
oc get route keycloak -n keycloak -o jsonpath='{.spec.host}'
```

### Access the Admin Console

1. Get the route hostname
2. Navigate to `https://<hostname>/admin`
3. Login with the admin credentials (default: admin/admin)

### Get Admin Credentials

```bash
oc get secret keycloak-admin -n keycloak -o jsonpath='{.data.admin-user}' | base64 -d
oc get secret keycloak-admin -n keycloak -o jsonpath='{.data.admin-password}' | base64 -d
```

## Production Considerations

### Production Requirements Overview

To run Keycloak in production mode, several key changes are required:

| Aspect | Development Mode | Production Mode |
|--------|------------------|-----------------|
| **Command** | `start-dev` | `start --optimized` |
| **Database** | H2 (in-memory) | PostgreSQL (persistent) |
| **Health Probe Port** | 9000 (management) | 8080 (main) |
| **Data Persistence** | Lost on restart | Persisted to database |
| **Admin Credentials** | admin/admin | **Must be changed** |
| **Replicas** | 1 | 2-3+ recommended |
| **Performance** | Not optimized | Pre-built & optimized |

### 1. Database Setup (Required)

For production deployments, use an external PostgreSQL database:

1. Deploy PostgreSQL separately or use a managed database service
2. Create a database for Keycloak:
   ```sql
   CREATE DATABASE keycloak;
   CREATE USER keycloak WITH ENCRYPTED PASSWORD 'secure-password';
   GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
   ```

### 2. Production Values Configuration

Create a complete `production-values.yaml` file with all required changes:

```yaml
# Production replica count
replicaCount: 3

# Production startup arguments
args:
  - start                          # Use 'start' instead of 'start-dev'
  - --optimized                    # Use pre-built optimized configuration
  - --http-enabled=true
  - --http-port=8080
  - --hostname-strict=false
  - --proxy-headers=xforwarded     # Required for OpenShift routes

# Admin credentials (CHANGE THESE!)
secret:
  adminUser: your-admin-username
  adminPassword: YourSecurePassword123!
  dbEnabled: true
  dbUrl: "jdbc:postgresql://postgres-host:5432/keycloak"
  dbUsername: keycloak
  dbPassword: your-secure-db-password

# CRITICAL: Health probes must use port 8080 in production mode
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080                     # Port 8080 for production (NOT 9000!)
  initialDelaySeconds: 120
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080                     # Port 8080 for production (NOT 9000!)
  initialDelaySeconds: 60
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

# Production resource limits
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi

# Optional: Enable persistence for custom themes/providers
persistence:
  enabled: true
  size: 5Gi

# High availability pod distribution
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - keycloak
          topologyKey: kubernetes.io/hostname
```

### 3. Deploy Production Instance

```bash
helm install keycloak ./helm -n keycloak \
  --create-namespace \
  -f production-values.yaml
```

### Critical Production Notes

⚠️ **Health Probe Port Configuration**
- **Development mode**: Health endpoints are on port 9000 (management interface)
- **Production mode**: Health endpoints are on port 8080 (main application port)
- Failing to change this will cause pods to fail readiness checks!

⚠️ **Security Requirements**
- Always change default admin credentials (admin/admin)
- Use strong, unique passwords for database access
- Consider using Kubernetes Secrets or External Secrets Operator for credential management

⚠️ **Database Requirement**
- Production mode (`start --optimized`) requires an external database
- H2 in-memory database is not available in production mode
- Ensure database is created and accessible before deploying

### 4. Additional Production Enhancements

**High Availability**: The production configuration above includes pod anti-affinity rules to distribute Keycloak pods across different nodes for improved resilience.

**Persistence**: Enabling persistent storage allows you to store custom themes, providers, and extensions that survive pod restarts.

**Resource Limits**: Adjust CPU and memory limits based on your expected load and usage patterns.

### Security Best Practices

1. **Change Default Credentials**: Always change the default admin credentials
2. **Use TLS**: Enable TLS termination at the route level
3. **Database Passwords**: Use strong, randomly generated passwords
4. **Network Policies**: Implement network policies to restrict access
5. **Resource Limits**: Set appropriate resource limits to prevent resource exhaustion
6. **Regular Updates**: Keep Keycloak updated to the latest stable version

## Upgrading

```bash
helm upgrade keycloak ./helm -n keycloak -f custom-values.yaml
```

## Uninstalling

```bash
helm uninstall keycloak -n keycloak
```

To also delete the persistent volume claims:

```bash
oc delete pvc -l app.kubernetes.io/name=keycloak -n keycloak
```

## Troubleshooting

### Pod Not Starting

Check pod logs:
```bash
oc logs -f deployment/keycloak -n keycloak
```

Check pod events:
```bash
oc describe pod -l app.kubernetes.io/name=keycloak -n keycloak
```

### Database Connection Issues

Verify database connectivity:
```bash
oc rsh deployment/keycloak -n keycloak
# Inside the pod
curl -v telnet://postgres-host:5432
```

Check database credentials:
```bash
oc get secret keycloak-db -n keycloak -o yaml
```

### Route Not Accessible

Check route status:
```bash
oc get route keycloak -n keycloak
oc describe route keycloak -n keycloak
```

Verify service endpoints:
```bash
oc get endpoints keycloak -n keycloak
```

## Support

For issues and questions:
- Keycloak Documentation: https://www.keycloak.org/documentation
- Keycloak GitHub: https://github.com/keycloak/keycloak
- OpenShift Documentation: https://docs.openshift.com/

## License

This Helm chart follows the same license as the parent project.
