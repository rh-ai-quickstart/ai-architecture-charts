# Keycloak Helm Chart Examples

This directory contains example values files for common deployment scenarios.

## Available Examples

### 1. Development (`dev-values.yaml`)

Quick setup for local development with relaxed security and simple passwords.

**Features:**
- Single replica
- Embedded H2 database (no external DB needed)
- HTTP allowed (no TLS required)
- Self-registration enabled
- Simple passwords
- localhost redirect URIs

**Usage:**
```bash
helm install keycloak ./helm --values examples/dev-values.yaml -n dev --create-namespace
```

**⚠️ WARNING:** Not suitable for production! Data is lost on pod restart.

---

### 2. Production (`production-values.yaml`)

Enterprise-grade configuration with high availability and strict security.

**Features:**
- 3 replicas for HA
- External PostgreSQL database
- HTTPS required
- Strong security settings
- No default users
- Pod anti-affinity
- Monitoring enabled

**Usage:**
```bash
# 1. Create database secret first
kubectl create secret generic keycloak-db-credentials \
  --from-literal=username=keycloak \
  --from-literal=password=<strong-password> \
  -n production

# 2. Customize production-values.yaml with your URLs

# 3. Deploy
helm install keycloak ./helm --values examples/production-values.yaml -n production --create-namespace
```

---

### 3. AI Platform (`ai-platform-values.yaml`)

Optimized for AI/ML application authentication with role-based access.

**Features:**
- AI-specific roles (data-scientist, ml-engineer, etc.)
- Multiple application redirect URIs
- Integration with pgvector database
- Longer session tokens for AI workflows
- Default users with role assignments

**Usage:**
```bash
helm install keycloak ./helm --values examples/ai-platform-values.yaml -n ai-platform --create-namespace
```

---

### 4. Minimal (`minimal-values.yaml`)

Bare minimum configuration using mostly chart defaults.

**Features:**
- Minimal overrides
- Uses all chart defaults
- Only specifies database connection

**Usage:**
```bash
helm install keycloak ./helm --values examples/minimal-values.yaml -n keycloak --create-namespace
```

---

### 5. Existing Database Secret (`with-existing-database-secret.yaml`)

Use when database credentials are managed separately (e.g., by external secrets operator).

**Features:**
- References existing Kubernetes secret
- No credential duplication
- Better secret management

**Usage:**
```bash
# 1. Create secret (or use existing one)
kubectl create secret generic my-db-secret \
  --from-literal=db-username=keycloak \
  --from-literal=db-password=myPassword \
  -n keycloak

# 2. Deploy
helm install keycloak ./helm --values examples/with-existing-database-secret.yaml -n keycloak --create-namespace
```

---

## Customization

These examples are starting points. Customize them for your needs:

```bash
# Copy an example
cp examples/production-values.yaml my-values.yaml

# Edit for your environment
vim my-values.yaml

# Deploy with your customizations
helm install keycloak ./helm --values my-values.yaml -n my-namespace --create-namespace
```

## Combining Values Files

You can layer multiple values files:

```bash
# Use production base + custom overrides
helm install keycloak ./helm \
  --values examples/production-values.yaml \
  --values my-custom-values.yaml \
  -n production --create-namespace
```

## Common Customizations

### Change Database Connection

```yaml
database:
  host: my-postgres.example.com
  port: 5432
  name: my_keycloak_db
  username: my_user
  password: my_password
```

### Add More Users

```yaml
realm:
  users:
    - username: newuser
      email: newuser@example.com
      firstName: New
      lastName: User
      enabled: true
      emailVerified: true
      credentials:
        - type: password
          value: password123
          temporary: false
      realmRoles:
        - user
```

### Change Resource Limits

```yaml
keycloak:
  resources:
    requests:
      memory: "2Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "4000m"
```

### Add Custom Realm Roles

```yaml
realm:
  roles:
    realm:
      - name: my-custom-role
        description: My custom role description
```

## Testing Your Configuration

Before deploying to production, test your configuration:

```bash
# 1. Dry run to see generated manifests
helm install keycloak ./helm \
  --values my-values.yaml \
  --dry-run --debug

# 2. Install in test namespace first
helm install keycloak ./helm \
  --values my-values.yaml \
  -n keycloak-test --create-namespace

# 3. Verify deployment
kubectl get keycloak -n keycloak-test
kubectl get keycloakrealmimport -n keycloak-test

# 4. Test login and functionality

# 5. Clean up test
helm uninstall keycloak -n keycloak-test
```

## Need Help?

- See main [README.md](../README.md) for detailed documentation
- Check [values.yaml](../values.yaml) for all available options
- Visit [Keycloak Documentation](https://www.keycloak.org/documentation)

