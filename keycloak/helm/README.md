# Keycloak Helm Chart

A Helm chart for deploying Red Hat Build of Keycloak on OpenShift/Kubernetes using the Keycloak Operator. This chart provides a production-ready Keycloak deployment with automated realm and user management.

## Features

✅ **Operator-based deployment** - Leverages Keycloak Operator for production-grade management  
✅ **Automated realm creation** - Creates realms and clients via KeycloakRealmImport CRs  
✅ **Default users** - Configurable default admin and test users  
✅ **Database integration** - Supports PostgreSQL, MySQL, MariaDB, MSSQL, Oracle  
✅ **OpenShift Route support** - Automatic route creation with TLS termination  
✅ **Pre-flight checks** - Validates operator installation before deployment  
✅ **Production-ready defaults** - Security, resource limits, and health checks configured  
✅ **Highly configurable** - Extensive values for customization

## Prerequisites

### Required

- **Kubernetes 1.24+** or **OpenShift 4.10+**
- **Helm 3.8+**
- **Keycloak Operator** installed (see [Installation](#operator-installation))
- **Cluster admin permissions** for operator installation

### Optional

- PostgreSQL database (or use embedded H2 for testing only)

## Operator Installation

⚠️ **IMPORTANT**: The Keycloak Operator must be installed **before** deploying this chart.

### OpenShift (Recommended)

```bash
# Via OpenShift Console
# 1. Navigate to: Operators → OperatorHub
# 2. Search for: "Red Hat Build of Keycloak Operator" or "Keycloak Operator"
# 3. Click "Install" and follow the prompts

# Or via CLI
oc create namespace keycloak-operator
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: keycloak-operator
  namespace: keycloak-operator
spec:
  channel: stable
  name: keycloak-operator
  source: community-operators
  sourceNamespace: openshift-marketplace
EOF
```

### Kubernetes

```bash
# Install Keycloak Operator CRDs and deployment
kubectl apply -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.0.7/kubernetes/kubernetes.yml

# Verify installation
kubectl get crd keycloaks.k8s.keycloak.org
kubectl get crd keycloakrealmimports.k8s.keycloak.org
```

## Quick Start

### 1. Add Helm Repository

```bash
helm repo add ai-charts https://rh-ai-quickstart.github.io/ai-architecture-charts
helm repo update
```

### 2. Install with Default Configuration

```bash
# Install with defaults (includes demo users)
helm install keycloak ai-charts/keycloak \
  --namespace keycloak \
  --create-namespace
```

### 3. Wait for Deployment

```bash
# Wait for Keycloak to be ready (takes 2-5 minutes)
kubectl wait --for=condition=Ready keycloak/keycloak -n keycloak --timeout=300s

# Get the Keycloak URL (OpenShift)
kubectl get route keycloak-ingress -n keycloak -o jsonpath='{.spec.host}'
```

### 4. Access Keycloak

```bash
# Get admin credentials
ADMIN_USER=$(kubectl get secret keycloak-initial-admin -n keycloak -o jsonpath='{.data.username}' | base64 -d)
ADMIN_PASS=$(kubectl get secret keycloak-initial-admin -n keycloak -o jsonpath='{.data.password}' | base64 -d)

echo "Admin Console: https://<keycloak-url>/admin"
echo "Username: $ADMIN_USER"
echo "Password: $ADMIN_PASS"
```

## Configuration

### Basic Configuration

The chart comes with sensible defaults. Override values as needed:

```bash
helm install keycloak ai-charts/keycloak \
  --namespace keycloak \
  --create-namespace \
  --set keycloak.replicas=2 \
  --set database.password=mySecurePassword
```

### Using a Values File

Create a `my-values.yaml`:

```yaml
keycloak:
  replicas: 2
  
database:
  host: postgresql.database.svc
  name: keycloak
  username: keycloak
  password: changeme

realm:
  name: my-platform
  displayName: "My AI Platform"
  
  client:
    id: my-app
    redirectUris:
      - "https://my-app.example.com/*"
    webOrigins:
      - "https://my-app.example.com"
  
  users:
    - username: admin
      email: admin@example.com
      firstName: Admin
      lastName: User
      enabled: true
      emailVerified: true
      credentials:
        - type: password
          value: AdminPassword123!
          temporary: false
      realmRoles:
        - admin
```

Deploy with custom values:

```bash
helm install keycloak ai-charts/keycloak \
  --namespace keycloak \
  --create-namespace \
  --values my-values.yaml
```

## Integration Examples

### Using with AI Applications

This chart is designed to integrate with AI architecture components:

```yaml
# values.yaml
realm:
  name: ai-platform
  client:
    id: ai-platform-client
    redirectUris:
      - "https://chatbot.example.com/*"
      - "https://rag-app.example.com/*"
    webOrigins:
      - "https://chatbot.example.com"
      - "https://rag-app.example.com"
```

### Using with pgvector Database

Reference the pgvector chart from ai-architecture-charts:

```yaml
# In your parent chart's Chart.yaml
dependencies:
  - name: pgvector
    version: "0.1.0"
    repository: "https://rh-ai-quickstart.github.io/ai-architecture-charts"
  - name: keycloak
    version: "0.1.0"
    repository: "https://rh-ai-quickstart.github.io/ai-architecture-charts"

# In your parent chart's values.yaml
pgvector:
  secret:
    dbname: keycloak
    user: keycloak
    password: changeme

keycloak:
  database:
    host: pgvector-postgresql
    name: keycloak
    username: keycloak
    password: changeme
```

### Application Integration

Configure your application to use Keycloak:

```bash
# OIDC Discovery URL
KEYCLOAK_URL=https://keycloak.example.com
OIDC_DISCOVERY_URL=$KEYCLOAK_URL/realms/ai-platform/.well-known/openid-configuration

# Client Configuration
CLIENT_ID=ai-platform-client
REDIRECT_URI=https://your-app.example.com/callback
```

## Configuration Reference

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `keycloak.replicas` | Number of Keycloak instances | `1` |
| `keycloak.resources.requests.memory` | Memory request | `512Mi` |
| `keycloak.resources.limits.memory` | Memory limit | `1Gi` |
| `database.enabled` | Use external database | `true` |
| `database.vendor` | Database type | `postgres` |
| `database.host` | Database hostname | `postgresql` |
| `database.port` | Database port | `5432` |
| `database.name` | Database name | `keycloak` |
| `database.username` | Database username | `keycloak` |
| `database.password` | Database password | `changeme` |
| `realm.enabled` | Create realm automatically | `true` |
| `realm.name` | Realm name | `ai-platform` |
| `realm.client.id` | Client ID | `ai-platform-client` |
| `preflight.enabled` | Run pre-flight checks | `true` |

### Complete Values

See [values.yaml](values.yaml) for all available configuration options.

## Common Scenarios

### Development Setup

```yaml
# dev-values.yaml
keycloak:
  replicas: 1
  resources:
    requests:
      memory: "256Mi"
      cpu: "100m"

database:
  enabled: false  # Use embedded H2 (not recommended for prod)

realm:
  users:
    - username: dev
      email: dev@example.com
      credentials:
        - type: password
          value: dev123
          temporary: false
```

### Production Setup

```yaml
# prod-values.yaml
keycloak:
  replicas: 3
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"

database:
  enabled: true
  vendor: postgres
  host: postgresql.production.svc
  name: keycloak_prod
  existingSecret:
    enabled: true
    name: keycloak-db-secret
    usernameKey: db-user
    passwordKey: db-password

realm:
  sslRequired: "all"
  registrationAllowed: false
  bruteForceProtected: true
  
  users: []  # Don't create default users in production
```

### Multiple Clients

```yaml
# Use KeycloakRealmImport CR to add more clients
# This chart supports one client via values, for multiple clients
# create additional KeycloakRealmImport resources
```

## Troubleshooting

### Operator Not Found

```bash
# Check if operator is installed
kubectl get crd keycloaks.k8s.keycloak.org

# If not found, install the operator first (see Prerequisites)
```

### Keycloak Pod Not Starting

```bash
# Check Keycloak status
kubectl describe keycloak keycloak -n keycloak

# Check pod logs
kubectl logs -l app=keycloak -n keycloak -f

# Common issues:
# - Database connection failed (check credentials)
# - Insufficient resources (increase limits)
# - Image pull errors (check network/registry)
```

### Realm Not Importing

```bash
# Check realm import status
kubectl describe keycloakrealmimport ai-platform -n keycloak

# Ensure Keycloak is ready first
kubectl get keycloak keycloak -n keycloak

# Delete and recreate if needed
kubectl delete keycloakrealmimport ai-platform -n keycloak
helm upgrade keycloak ai-charts/keycloak -n keycloak --reuse-values
```

### Route Not Created

```bash
# Check if route is enabled
kubectl get route -n keycloak

# On non-OpenShift, use port-forward instead
kubectl port-forward svc/keycloak-service 8080:8080 -n keycloak
```

## Upgrading

```bash
# Update Helm repository
helm repo update

# Upgrade deployment
helm upgrade keycloak ai-charts/keycloak \
  --namespace keycloak \
  --values my-values.yaml

# Verify upgrade
kubectl get keycloak keycloak -n keycloak
```

## Uninstalling

```bash
# Uninstall the chart
helm uninstall keycloak -n keycloak

# Note: The operator and CRDs remain installed
# To remove operator (affects all Keycloak instances):
# kubectl delete -f https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/26.0.7/kubernetes/kubernetes.yml
```

## Security Considerations

⚠️ **Important Security Notes**

1. **Change default passwords** - Never use default passwords in production
2. **Use TLS** - Always enable TLS for production (`sslRequired: "all"`)
3. **Secure database** - Use strong database credentials and TLS
4. **Limit CORS** - Configure specific web origins, not wildcards
5. **Restrict redirects** - Use specific redirect URIs, not wildcards
6. **Enable brute force protection** - Already enabled by default
7. **Regular updates** - Keep Keycloak and operator updated
8. **Use secrets** - Store credentials in Kubernetes secrets, not values files
9. **RBAC** - Configure proper role-based access control
10. **Audit logs** - Enable and monitor Keycloak audit logs

## Architecture

This chart deploys:

- **Keycloak CR** - Defines the Keycloak instance (managed by operator)
- **KeycloakRealmImport CR** - Defines realm, clients, and users
- **Secret** - Stores database credentials (if not using existing secret)
- **ServiceAccount** - For pre-flight checks and jobs
- **ClusterRole/Binding** - RBAC for pre-flight validation
- **Pre-flight Job** - Validates operator installation before deployment

The Keycloak Operator creates:
- **StatefulSet** - Keycloak pods
- **Service** - Internal service
- **Route/Ingress** - External access (if enabled)
- **Admin Secret** - Initial admin credentials

## Contributing

This chart is part of the [ai-architecture-charts](https://github.com/rh-ai-quickstart/ai-architecture-charts) repository.

To contribute:
1. Fork the repository
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak Operator Guide](https://www.keycloak.org/guides#operator)
- [Keycloak on OpenShift](https://www.keycloak.org/getting-started/getting-started-openshift)
- [AI Architecture Charts](https://github.com/rh-ai-quickstart/ai-architecture-charts)

## License

This chart is licensed under the Apache License 2.0. See LICENSE for details.

Keycloak is licensed under the Apache License 2.0.

