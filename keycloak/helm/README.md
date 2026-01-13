# Keycloak Helm Chart

This Helm chart deploys Keycloak (Quarkus-based distribution) on OpenShift for identity and access management.

## Overview

Keycloak is an open-source identity and access management solution that provides:
- Single Sign-On (SSO)
- Identity brokering and social login
- User federation (LDAP/Active Directory)
- OAuth 2.0 and OpenID Connect support
- SAML 2.0 support
- Fine-grained authorization

This chart deploys Keycloak 26.x (Quarkus-based) without the operator, making it simpler and more consistent with other charts in this repository.

## Prerequisites

- OpenShift cluster (4.12+)
- Helm 3.x
- PostgreSQL database (recommended for production)
  - Can use the `pgvector` chart from this repository

## Installation

### Quick Start (Development)

Deploy Keycloak with embedded H2 database (not recommended for production):

```bash
helm install keycloak ./helm \
  --namespace keycloak \
  --create-namespace \
  --set database.vendor=dev-file
```

### Production Deployment with PostgreSQL

1. **Deploy PostgreSQL** (using pgvector chart):

```bash
helm install keycloak-db ../pgvector/helm \
  --namespace keycloak \
  --create-namespace \
  --set secret.dbname=keycloak \
  --set secret.user=keycloak \
  --set secret.password=secure-password
```

2. **Deploy Keycloak**:

```bash
helm install keycloak ./helm \
  --namespace keycloak \
  --set database.vendor=postgres \
  --set database.host=keycloak-db-postgresql \
  --set database.database=keycloak \
  --set database.username=keycloak \
  --set database.password=secure-password \
  --set auth.adminPassword=admin-secure-password
```

### Using Existing Database Secret

If you have an existing secret with database credentials:

```bash
helm install keycloak ./helm \
  --namespace keycloak \
  --set database.vendor=postgres \
  --set database.host=postgresql.database.svc.cluster.local \
  --set database.database=keycloak \
  --set database.existingSecret=my-db-secret \
  --set database.existingSecretUsernameKey=username \
  --set database.existingSecretPasswordKey=password
```

## Configuration

### Key Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Keycloak image repository | `quay.io/keycloak/keycloak` |
| `image.tag` | Keycloak image tag | `26.0.7` |
| `replicas` | Number of Keycloak replicas | `1` |
| `auth.adminUser` | Admin username | `admin` |
| `auth.adminPassword` | Admin password | `changeme` |
| `database.vendor` | Database vendor (`postgres`, `dev-file`) | `postgres` |
| `database.host` | Database host | `""` (defaults to pgvector-postgresql) |
| `database.port` | Database port | `5432` |
| `database.database` | Database name | `keycloak` |
| `database.username` | Database username | `keycloak` |
| `database.password` | Database password | `""` |
| `database.existingSecret` | Use existing secret for DB credentials | `""` |
| `hostname.hostname` | Keycloak hostname (leave empty for auto) | `""` |
| `hostname.strict` | Enable strict hostname checking | `false` |
| `route.enabled` | Create OpenShift route | `true` |
| `route.host` | Custom route hostname | `""` (auto-generated) |
| `route.tls.enabled` | Enable TLS for route | `true` |
| `route.tls.termination` | TLS termination type | `edge` |
| `openshiftOAuth.enabled` | Enable OpenShift OAuth integration | `true` |
| `resources.requests.cpu` | CPU request | `500m` |
| `resources.requests.memory` | Memory request | `1Gi` |
| `resources.limits.cpu` | CPU limit | `2000m` |
| `resources.limits.memory` | Memory limit | `2Gi` |

### Database Configuration

#### PostgreSQL (Recommended for Production)

```yaml
database:
  vendor: postgres
  host: postgresql.namespace.svc.cluster.local
  port: 5432
  database: keycloak
  username: keycloak
  password: secure-password
```

#### Embedded H2 (Development Only)

```yaml
database:
  vendor: dev-file
```

**⚠️ Warning**: Embedded H2 database is not suitable for production use and does not support high availability.

### Hostname Configuration

For production deployments, configure a proper hostname:

```yaml
hostname:
  hostname: auth.example.com
  strict: true
  strictBackchannel: false
```

If you're using OpenShift routes with auto-generated hostnames, keep `hostname.strict: false`.

### Resource Requirements

Adjust based on your workload:

```yaml
resources:
  requests:
    cpu: 1000m
    memory: 2Gi
  limits:
    cpu: 4000m
    memory: 4Gi
```

### High Availability

For HA deployments:

```yaml
replicas: 3

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/name: keycloak
        topologyKey: kubernetes.io/hostname
```

## Automated Realm and Client Configuration

### Realm Import

You can pre-configure Keycloak with realms, clients, users, and roles by enabling realm import. This allows you to deploy Keycloak with a complete configuration from the Helm chart.

#### Enable Realm Import

Create a realm configuration file (JSON format) and add it to your values.yaml:

```yaml
realmImport:
  enabled: true
  realms:
    ai-apps-realm.json: |
      {
        "realm": "ai-apps",
        "enabled": true,
        "clients": [
          {
            "clientId": "llama-stack",
            "enabled": true,
            "protocol": "openid-connect",
            "publicClient": false,
            "redirectUris": ["https://llama-stack.example.com/*"],
            "webOrigins": ["https://llama-stack.example.com"],
            "serviceAccountsEnabled": true
          }
        ],
        "roles": {
          "realm": [
            {"name": "user"},
            {"name": "admin"}
          ]
        }
      }
```

#### Deploy with Realm Import

```bash
helm install keycloak ./helm \
  --namespace keycloak \
  --values examples/values-with-realm-import.yaml
```

#### Export Existing Realm Configuration

To export an existing realm for use in realm import:

```bash
# Port-forward to Keycloak
oc port-forward svc/keycloak 8080:8080 -n keycloak

# Export realm using Keycloak admin CLI
docker run --rm --network=host quay.io/keycloak/keycloak:26.0.7 \
  export --dir /tmp/export --realm ai-apps --users realm_file

# Or use the admin console:
# Realm Settings → Action → Partial export
```

#### Example Realm Configurations

See the `examples/` directory for complete realm configurations:
- `examples/ai-apps-realm.json` - Complete AI applications realm with multiple clients
- `examples/values-with-realm-import.yaml` - Values file with realm import enabled

**Note**: Realm import runs on every Keycloak startup. For updates to existing realms, consider using the Keycloak Admin API or CLI instead.

## OpenShift OAuth Integration

By default, this chart creates resources to enable OpenShift as an identity provider in Keycloak, allowing users to login to Keycloak-protected applications using their OpenShift credentials.

### How It Works

When `openshiftOAuth.enabled: true` (default), the chart creates:
- A ServiceAccount with OAuth redirect annotations
- A service account token secret for authentication

### Configuration Steps

After installing the chart, configure OpenShift as an IdP in Keycloak:

1. **Get the ServiceAccount token**:
   ```bash
   TOKEN=$(oc serviceaccounts get-token keycloak-oauth -n keycloak)
   ```

2. **Get OpenShift API server URL**:
   ```bash
   OPENSHIFT_URL=$(oc whoami --show-server)
   ```

3. **Login to Keycloak admin console** and navigate to:
   - Identity Providers → Add provider → OpenID Connect v1.0

4. **Configure the provider** with these settings:
   - **Alias**: `openshift`
   - **Display name**: `OpenShift`
   - **Authorization URL**: `${OPENSHIFT_URL}/oauth/authorize`
   - **Token URL**: `${OPENSHIFT_URL}/oauth/token`
   - **Client Authentication**: Client secret sent as post
   - **Client ID**: `system:serviceaccount:keycloak:keycloak-oauth`
   - **Client Secret**: `<paste the TOKEN from step 1>`

5. **Test** by logging out and selecting "OpenShift" as the login provider

### Disable OpenShift OAuth

To disable this integration:

```bash
helm install keycloak ./helm \
  --set openshiftOAuth.enabled=false
```

## Integration Examples

### Integration with PGVector Chart

Use the pgvector chart from this repository as the database:

```bash
# Deploy database
helm install keycloak-db ../pgvector/helm \
  --namespace keycloak \
  --create-namespace \
  --set secret.dbname=keycloak \
  --set secret.user=keycloak \
  --set secret.password=keycloak-password

# Deploy Keycloak
helm install keycloak ./helm \
  --namespace keycloak \
  --set database.vendor=postgres \
  --set database.host=keycloak-db-postgresql \
  --set database.database=keycloak \
  --set database.username=keycloak \
  --set database.password=keycloak-password
```

### Protecting AI Applications with Keycloak

This section shows how to integrate your applications with Keycloak for authentication and authorization.

#### Step 1: Create a Realm

1. Login to Keycloak admin console
2. Create a new realm (e.g., `ai-apps`)
3. Configure realm settings:
   - Login settings (password policies, session timeouts, etc.)
   - Theme customization
   - Email configuration

#### Step 2: Create a Client for Your Application

For each application you want to protect:

1. Navigate to: **Clients** → **Create client**
2. Configure the client:
   - **Client ID**: `my-app` (your application name)
   - **Client Protocol**: `openid-connect`
   - **Client Authentication**: `On` (for confidential clients like web apps)
   - **Valid Redirect URIs**: `https://my-app.example.com/*`
   - **Web Origins**: `https://my-app.example.com`

3. After saving, go to the **Credentials** tab and copy the **Client Secret**

#### Step 3: Configure Your Application

##### For Python Applications (Flask/FastAPI)

Install the library:
```bash
pip install python-keycloak
```

Example configuration:
```python
from keycloak import KeycloakOpenID

# Keycloak configuration
keycloak_openid = KeycloakOpenID(
    server_url="https://keycloak-route.example.com/",
    client_id="my-app",
    realm_name="ai-apps",
    client_secret_key="your-client-secret"
)

# Get access token
token = keycloak_openid.token(username="user", password="password")

# Verify token
userinfo = keycloak_openid.userinfo(token['access_token'])
```

##### For Node.js Applications

Install the library:
```bash
npm install keycloak-connect express-session
```

Example configuration:
```javascript
const session = require('express-session');
const Keycloak = require('keycloak-connect');

const memoryStore = new session.MemoryStore();
const keycloak = new Keycloak({ store: memoryStore }, {
  realm: 'ai-apps',
  'auth-server-url': 'https://keycloak-route.example.com/',
  'ssl-required': 'external',
  resource: 'my-app',
  credentials: {
    secret: 'your-client-secret'
  }
});

app.use(keycloak.middleware());
app.get('/protected', keycloak.protect(), (req, res) => {
  res.send('This is a protected route');
});
```

##### For Applications Running in OpenShift

Use environment variables to configure your app:

```yaml
# deployment.yaml
env:
- name: KEYCLOAK_URL
  value: "https://keycloak-keycloak.svc.cluster.local:8080"
- name: KEYCLOAK_REALM
  value: "ai-apps"
- name: KEYCLOAK_CLIENT_ID
  value: "my-app"
- name: KEYCLOAK_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: my-app-keycloak-secret
      key: client-secret
```

#### Step 4: Protect Specific Routes

Configure which routes require authentication:

**Public routes**: No authentication needed (e.g., `/health`, `/metrics`)
**Protected routes**: Require valid JWT token (e.g., `/api/*`)
**Admin routes**: Require specific roles (e.g., `/admin/*`)

#### Step 5: Set Up Roles and Permissions

1. **Create Roles**:
   - Navigate to: **Realm Roles** → **Create role**
   - Example roles: `user`, `admin`, `ai-operator`

2. **Assign Roles to Users**:
   - Navigate to: **Users** → Select user → **Role mapping**
   - Add roles to the user

3. **Configure Client Scopes**:
   - Navigate to: **Clients** → Your client → **Client scopes**
   - Add role mappings to include in tokens

#### Example: Protecting LlamaStack with Keycloak

1. **Create Keycloak client** for LlamaStack:
   ```bash
   # In Keycloak admin console
   Client ID: llama-stack
   Root URL: https://llama-stack.example.com
   Valid Redirect URIs: https://llama-stack.example.com/*
   ```

2. **Configure LlamaStack** to use Keycloak:
   ```yaml
   # In your LlamaStack deployment
   env:
   - name: OIDC_ENABLED
     value: "true"
   - name: OIDC_ISSUER
     value: "https://keycloak.example.com/realms/ai-apps"
   - name: OIDC_CLIENT_ID
     value: "llama-stack"
   - name: OIDC_CLIENT_SECRET
     valueFrom:
       secretKeyRef:
         name: llama-stack-oidc
         key: client-secret
   ```

3. **Test authentication**:
   ```bash
   # Get access token
   curl -X POST "https://keycloak.example.com/realms/ai-apps/protocol/openid-connect/token" \
     -d "client_id=llama-stack" \
     -d "client_secret=YOUR_SECRET" \
     -d "grant_type=client_credentials"

   # Call protected API
   curl -H "Authorization: Bearer $ACCESS_TOKEN" \
     https://llama-stack.example.com/api/models
   ```

#### Common Integration Patterns

**1. Service-to-Service Authentication (Machine-to-Machine)**
```bash
# Use client_credentials grant type
# No user interaction required
curl -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=client_credentials"
```

**2. Web Application Authentication (Authorization Code Flow)**
```bash
# User redirected to Keycloak login page
# After login, redirect back with authorization code
# Exchange code for access token
curl -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=authorization_code" \
  -d "code=${AUTH_CODE}" \
  -d "redirect_uri=${REDIRECT_URI}"
```

**3. API Authentication (Resource Owner Password Flow)**
```bash
# Direct authentication with username/password
# Use only for trusted applications
curl -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=password" \
  -d "username=${USERNAME}" \
  -d "password=${PASSWORD}"
```

#### Token Validation

Validate JWT tokens in your application:

```python
import jwt
from jwt import PyJWKClient

# Get Keycloak's public key
jwks_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"
jwks_client = PyJWKClient(jwks_url)

# Validate token
signing_key = jwks_client.get_signing_key_from_jwt(token)
decoded_token = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256"],
    audience="my-app",
    options={"verify_exp": True}
)
```

#### Additional Resources

- [Keycloak Authorization Services](https://www.keycloak.org/docs/latest/authorization_services/)
- [Securing Applications Guide](https://www.keycloak.org/docs/latest/securing_apps/)
- [OpenID Connect Specification](https://openid.net/connect/)
- [OAuth 2.0 Specification](https://oauth.net/2/)

## Accessing Keycloak

### Admin Console

After deployment, get the route URL:

```bash
oc get route keycloak -n keycloak -o jsonpath='{.spec.host}'
```

Access the admin console at: `https://<HOSTNAME>/admin`

Default credentials:
- Username: `admin`
- Password: `changeme` (change this in production!)

### Retrieve Admin Credentials from Secret

```bash
oc get secret keycloak -n keycloak -o jsonpath='{.data.admin-username}' | base64 -d
oc get secret keycloak -n keycloak -o jsonpath='{.data.admin-password}' | base64 -d
```

## Health Checks

Keycloak provides built-in health endpoints:

- `/health` - Overall health status
- `/health/live` - Liveness check
- `/health/ready` - Readiness check

Access health endpoints:

```bash
KEYCLOAK_POD=$(oc get pods -l app.kubernetes.io/name=keycloak -n keycloak -o jsonpath='{.items[0].metadata.name}')
oc exec -it $KEYCLOAK_POD -n keycloak -- curl http://localhost:8080/health
```

## Monitoring

### Check Deployment Status

```bash
# Check deployment
oc get deployment keycloak -n keycloak

# Check pods
oc get pods -l app.kubernetes.io/name=keycloak -n keycloak

# View logs
oc logs -l app.kubernetes.io/name=keycloak -n keycloak -f
```

### Common Monitoring Commands

```bash
# Check if Keycloak is ready
oc get pods -l app.kubernetes.io/name=keycloak -n keycloak -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}'

# Check resource usage
oc adm top pods -l app.kubernetes.io/name=keycloak -n keycloak

# Get recent events
oc get events -n keycloak --sort-by='.lastTimestamp' | grep keycloak
```

## Troubleshooting

### Pod Not Starting

1. **Check pod status**:
   ```bash
   oc describe pod -l app.kubernetes.io/name=keycloak -n keycloak
   ```

2. **Check logs**:
   ```bash
   oc logs -l app.kubernetes.io/name=keycloak -n keycloak
   ```

3. **Verify database connectivity** (if using external DB):
   ```bash
   oc logs -l app.kubernetes.io/name=keycloak -n keycloak | grep -i "database\|connection"
   ```

### Database Connection Issues

1. **Verify database is running**:
   ```bash
   oc get pods -n keycloak | grep postgresql
   ```

2. **Test database connectivity**:
   ```bash
   oc run -it --rm debug --image=postgres:15 --restart=Never -- \
     psql -h keycloak-db-postgresql -U keycloak -d keycloak
   ```

3. **Check database credentials**:
   ```bash
   oc get secret keycloak -n keycloak -o jsonpath='{.data}' | jq
   ```

### Route/Hostname Issues

1. **Check route status**:
   ```bash
   oc get route keycloak -n keycloak
   ```

2. **Verify route is accessible**:
   ```bash
   ROUTE=$(oc get route keycloak -n keycloak -o jsonpath='{.spec.host}')
   curl -k https://$ROUTE/health
   ```

3. **If hostname strict mode is causing issues**, disable it:
   ```bash
   helm upgrade keycloak ./helm \
     --namespace keycloak \
     --reuse-values \
     --set hostname.strict=false
   ```

### Performance Issues

1. **Increase resource limits**:
   ```yaml
   resources:
     requests:
       cpu: 1000m
       memory: 2Gi
     limits:
       cpu: 4000m
       memory: 4Gi
   ```

2. **Scale horizontally**:
   ```bash
   helm upgrade keycloak ./helm \
     --namespace keycloak \
     --reuse-values \
     --set replicas=3
   ```

3. **Check database performance** - ensure PostgreSQL is properly tuned

## Upgrading

### Upgrade Helm Chart

```bash
helm upgrade keycloak ./helm \
  --namespace keycloak \
  --reuse-values
```

### Upgrade Keycloak Version

Update the image tag:

```bash
helm upgrade keycloak ./helm \
  --namespace keycloak \
  --reuse-values \
  --set image.tag=26.1.0
```

**Note**: Always review [Keycloak upgrade documentation](https://www.keycloak.org/docs/latest/upgrading/) before upgrading.

## Security Considerations

### Production Checklist

- [ ] Change default admin password
- [ ] Use external PostgreSQL database (not H2)
- [ ] Enable TLS on routes
- [ ] Configure hostname properly
- [ ] Set appropriate resource limits
- [ ] Enable proper logging and monitoring
- [ ] Regularly backup the database
- [ ] Keep Keycloak updated to latest stable version
- [ ] Review and apply Keycloak security best practices

### Secrets Management

All sensitive data is stored in Kubernetes secrets:

```bash
# View secret keys (not values)
oc get secret keycloak -n keycloak -o jsonpath='{.data}' | jq 'keys'

# Update admin password
oc create secret generic keycloak \
  --from-literal=admin-username=admin \
  --from-literal=admin-password=new-secure-password \
  --dry-run=client -o yaml | oc apply -f -
```

## Uninstallation

```bash
helm uninstall keycloak -n keycloak
```

**Warning**: This does not delete the PostgreSQL database. Delete separately if needed:

```bash
helm uninstall keycloak-db -n keycloak
```

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [Keycloak Admin Guide](https://www.keycloak.org/docs/latest/server_admin/)
- [Keycloak on Kubernetes Guide](https://www.keycloak.org/operator/installation)
- [OpenID Connect Specification](https://openid.net/connect/)

## Contributing

When contributing to this chart:

1. Follow the patterns established in other charts in this repository
2. Test with both embedded H2 and external PostgreSQL
3. Verify OpenShift route creation
4. Update this README with any new configuration options
5. Test upgrade scenarios

## License

This Helm chart is provided under the same license as the ai-architecture-charts repository.
