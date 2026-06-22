# Keycloak Realm Import Guide

This guide shows how to pre-configure Keycloak with realms, clients, users, and roles directly from your Helm values.

## Quick Example

```yaml
# values.yaml
realmImport:
  enabled: true
  realms:
    # Key is the realm name
    ai-apps:
      enabled: true
      clients:
      - clientId: my-app
        enabled: true
        protocol: openid-connect
        redirectUris:
        - https://my-app.example.com/*
        serviceAccountsEnabled: true
      roles:
        realm:
        - name: user
        - name: admin
      users:
      - username: admin
        enabled: true
        credentials:
        - type: password
          value: changeme
          temporary: false
        realmRoles:
        - admin
```

## How It Works

1. **Define realms in clean YAML** - no JSON needed in values.yaml
2. **Key becomes realm name** - no need to repeat `realm: ai-apps`
3. **Template converts to JSON** - Keycloak reads JSON files on startup
4. **Automatic import** - Realm is created when Keycloak starts

## Complete Example

```yaml
realmImport:
  enabled: true
  realms:
    # Define multiple realms
    ai-apps:
      enabled: true
      displayName: AI Applications
      sslRequired: external
      registrationAllowed: false
      loginWithEmailAllowed: true

      # OAuth/OIDC clients for your applications
      clients:
      - clientId: llama-stack
        name: LlamaStack AI Service
        enabled: true
        protocol: openid-connect
        publicClient: false
        redirectUris:
        - https://llama-stack-*.apps.example.com/*
        webOrigins:
        - https://llama-stack-*.apps.example.com
        serviceAccountsEnabled: true
        directAccessGrantsEnabled: true
        standardFlowEnabled: true

      - clientId: ingestion-pipeline
        name: Ingestion Pipeline
        enabled: true
        protocol: openid-connect
        publicClient: false
        redirectUris:
        - https://ingestion-*.apps.example.com/*
        serviceAccountsEnabled: true

      # Realm-level roles
      roles:
        realm:
        - name: user
          description: Standard user
        - name: admin
          description: Administrator
        - name: ai-operator
          description: AI services operator
        - name: data-scientist
          description: Data scientist with model access

      # Pre-create users
      users:
      - username: admin
        enabled: true
        emailVerified: true
        email: admin@example.com
        firstName: Admin
        lastName: User
        credentials:
        - type: password
          value: secure-password
          temporary: false
        realmRoles:
        - admin
        - ai-operator

      - username: demo
        enabled: true
        email: demo@example.com
        credentials:
        - type: password
          value: demo123
          temporary: true  # Force password change on first login
        realmRoles:
        - user

      # User groups
      groups:
      - name: AI Developers
        path: /AI Developers
        realmRoles:
        - ai-operator
        - user
      - name: Administrators
        path: /Administrators
        realmRoles:
        - admin
        - ai-operator

    # Another realm for different environment
    production:
      enabled: true
      clients:
      - clientId: prod-app
        enabled: true
        protocol: openid-connect
        serviceAccountsEnabled: true
```

## Deploy with Realm Import

```bash
# Using example values file
helm install keycloak ./helm \
  --namespace keycloak \
  --create-namespace \
  --values examples/values-with-realm-import.yaml

# Or with custom values
helm install keycloak ./helm \
  --namespace keycloak \
  --set realmImport.enabled=true \
  --set-file realmImport.realms.my-realm=/path/to/realm-config.yaml
```

## What Gets Created

When you deploy with realm import enabled:

1. **ConfigMap** - Contains realm configuration as JSON
2. **Volume Mount** - Mounts ConfigMap to `/opt/keycloak/data/import`
3. **Import Flag** - Keycloak starts with `--import-realm` argument
4. **Realm Created** - On startup, Keycloak imports all realms

## Verify Import

```bash
# Check if realm was imported
oc logs deployment/keycloak -n keycloak | grep -i import

# Login to admin console and verify
# https://keycloak-route/admin
```

## Common Client Configurations

### Service-to-Service (Machine-to-Machine)

```yaml
clients:
- clientId: backend-service
  enabled: true
  protocol: openid-connect
  publicClient: false
  serviceAccountsEnabled: true
  directAccessGrantsEnabled: false
  standardFlowEnabled: false
```

### Web Application

```yaml
clients:
- clientId: web-app
  enabled: true
  protocol: openid-connect
  publicClient: false
  redirectUris:
  - https://web-app.example.com/*
  - https://web-app.example.com/callback
  webOrigins:
  - https://web-app.example.com
  standardFlowEnabled: true
  directAccessGrantsEnabled: true
```

### Single Page Application (SPA)

```yaml
clients:
- clientId: spa-app
  enabled: true
  protocol: openid-connect
  publicClient: true  # No client secret
  redirectUris:
  - https://spa.example.com/*
  webOrigins:
  - https://spa.example.com
  standardFlowEnabled: true
  implicitFlowEnabled: false
```

## Important Notes

### Realm Import Behavior

- ✅ **Creates new realms** on first startup
- ⚠️ **Skips existing realms** by default (won't overwrite)
- ⚠️ **Runs on every startup** but only imports missing realms
- ⚠️ **Not for updates** - use Admin API or console for changes

### Security Considerations

- 🔒 Change default passwords before deploying to production
- 🔒 Store sensitive data in Kubernetes secrets, not values.yaml
- 🔒 Use `temporary: true` for user passwords to force change
- 🔒 Review client configurations for security settings

### Updating Existing Realms

For updating realms after initial import, use one of these methods:

1. **Admin Console** - Manual changes via web UI
2. **Admin API** - Programmatic updates
3. **Realm Export/Import** - Export, modify, delete realm, re-import
4. **Keycloak Admin CLI** - Command-line administration

## Troubleshooting

### Realm Not Imported

Check logs:
```bash
oc logs deployment/keycloak -n keycloak | grep -i "import\|realm"
```

Common issues:
- ConfigMap not mounted - check volumes
- Invalid JSON - Helm template syntax error
- Realm already exists - delete and re-import

### Get Realm Export

Export existing realm to use as template:

```bash
# Port-forward to Keycloak
oc port-forward svc/keycloak 8080:8080 -n keycloak

# Export realm
curl -X GET "http://localhost:8080/admin/realms/ai-apps" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" | jq > realm-export.json
```

## Additional Resources

- See `examples/values-with-realm-import.yaml` for complete example
- See `examples/ai-apps-realm.json` for full realm JSON structure
- [Keycloak Server Administration](https://www.keycloak.org/docs/latest/server_admin/)
- [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/)
