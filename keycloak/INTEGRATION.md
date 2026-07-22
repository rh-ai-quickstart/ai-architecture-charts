# Keycloak Application Integration Quick Reference

This guide provides quick reference examples for integrating your applications with Keycloak.

## Quick Start Checklist

- [ ] Deploy Keycloak using the Helm chart
- [ ] Create a realm for your applications
- [ ] Create a client in Keycloak for your app
- [ ] Get client credentials (client ID and secret)
- [ ] Configure your application to use Keycloak
- [ ] Test authentication flow

## Environment Variables

Standard environment variables for Keycloak integration:

```bash
# Keycloak Server
export KEYCLOAK_URL="https://keycloak-route.example.com"
export KEYCLOAK_REALM="ai-apps"

# Client Credentials
export KEYCLOAK_CLIENT_ID="my-app"
export KEYCLOAK_CLIENT_SECRET="your-secret-here"

# Token Endpoints
export TOKEN_URL="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token"
export AUTH_URL="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth"
export USERINFO_URL="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/userinfo"
export JWKS_URL="${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/certs"
```

## Common OAuth 2.0 Flows

### 1. Client Credentials (Service-to-Service)

Best for: Backend services, APIs, microservices

```bash
curl -X POST "${TOKEN_URL}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${KEYCLOAK_CLIENT_ID}" \
  -d "client_secret=${KEYCLOAK_CLIENT_SECRET}" \
  -d "grant_type=client_credentials"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI...",
  "expires_in": 300,
  "token_type": "Bearer"
}
```

### 2. Password Grant (Resource Owner)

Best for: Trusted first-party applications

```bash
curl -X POST "${TOKEN_URL}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${KEYCLOAK_CLIENT_ID}" \
  -d "client_secret=${KEYCLOAK_CLIENT_SECRET}" \
  -d "grant_type=password" \
  -d "username=${USERNAME}" \
  -d "password=${PASSWORD}"
```

### 3. Authorization Code Flow (Web Apps)

Best for: Web applications with user login

**Step 1: Redirect to Keycloak**
```
https://keycloak.example.com/realms/ai-apps/protocol/openid-connect/auth?
  client_id=my-app&
  redirect_uri=https://my-app.example.com/callback&
  response_type=code&
  scope=openid
```

**Step 2: Exchange code for token**
```bash
curl -X POST "${TOKEN_URL}" \
  -d "client_id=${KEYCLOAK_CLIENT_ID}" \
  -d "client_secret=${KEYCLOAK_CLIENT_SECRET}" \
  -d "grant_type=authorization_code" \
  -d "code=${AUTHORIZATION_CODE}" \
  -d "redirect_uri=https://my-app.example.com/callback"
```

## Python Integration Examples

### FastAPI with Keycloak

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from keycloak import KeycloakOpenID
import jwt
from jwt import PyJWKClient

app = FastAPI()

# Keycloak configuration
keycloak_openid = KeycloakOpenID(
    server_url="https://keycloak.example.com/",
    client_id="my-app",
    realm_name="ai-apps",
    client_secret_key="your-client-secret"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Verify token
        userinfo = keycloak_openid.userinfo(token)
        return userinfo
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/api/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['preferred_username']}"}

@app.get("/api/public")
async def public_route():
    return {"message": "This is public"}
```

### Flask with Keycloak

```python
from flask import Flask, request, jsonify
from keycloak import KeycloakOpenID
from functools import wraps

app = Flask(__name__)

keycloak_openid = KeycloakOpenID(
    server_url="https://keycloak.example.com/",
    client_id="my-app",
    realm_name="ai-apps",
    client_secret_key="your-client-secret"
)

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401

        try:
            userinfo = keycloak_openid.userinfo(token)
            return f(userinfo, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401

    return decorated_function

@app.route('/api/protected')
@require_token
def protected_route(userinfo):
    return jsonify({
        'message': f"Hello {userinfo['preferred_username']}",
        'roles': userinfo.get('realm_access', {}).get('roles', [])
    })

@app.route('/api/public')
def public_route():
    return jsonify({'message': 'This is public'})
```

## OpenShift Deployment Integration

### ConfigMap with Keycloak Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-app-config
data:
  keycloak.url: "https://keycloak-keycloak.svc.cluster.local:8080"
  keycloak.realm: "ai-apps"
  keycloak.client-id: "my-app"
```

### Secret with Client Credentials

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-app-keycloak
type: Opaque
stringData:
  client-secret: "your-client-secret-here"
```

### Deployment with Keycloak Integration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-app:latest
        env:
        - name: KEYCLOAK_URL
          valueFrom:
            configMapKeyRef:
              name: my-app-config
              key: keycloak.url
        - name: KEYCLOAK_REALM
          valueFrom:
            configMapKeyRef:
              name: my-app-config
              key: keycloak.realm
        - name: KEYCLOAK_CLIENT_ID
          valueFrom:
            configMapKeyRef:
              name: my-app-config
              key: keycloak.client-id
        - name: KEYCLOAK_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: my-app-keycloak
              key: client-secret
        ports:
        - containerPort: 8080
```

## Testing Authentication

### Get Access Token

```bash
# Store credentials
export KEYCLOAK_URL="https://keycloak.example.com"
export REALM="ai-apps"
export CLIENT_ID="my-app"
export CLIENT_SECRET="your-secret"

# Get token
TOKEN=$(curl -s -X POST \
  "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=client_credentials" | jq -r '.access_token')

echo "Token: ${TOKEN}"
```

### Call Protected API

```bash
# Use token to call API
curl -H "Authorization: Bearer ${TOKEN}" \
  https://my-app.example.com/api/protected
```

### Decode JWT Token

```bash
# Decode token (requires jq)
echo $TOKEN | cut -d. -f2 | base64 -d | jq
```

## Role-Based Access Control

### Check User Roles in Token

```python
import jwt

def check_roles(token, required_roles):
    """Check if user has required roles"""
    decoded = jwt.decode(token, options={"verify_signature": False})
    user_roles = decoded.get('realm_access', {}).get('roles', [])

    return all(role in user_roles for role in required_roles)

# Example usage
if check_roles(token, ['admin']):
    # Allow access
    pass
else:
    # Deny access
    raise PermissionError("Insufficient permissions")
```

### Protect Routes by Role (FastAPI)

```python
from fastapi import Depends, HTTPException

def require_roles(*required_roles):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_roles = current_user.get('realm_access', {}).get('roles', [])
        if not all(role in user_roles for role in required_roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

@app.get("/api/admin")
async def admin_route(user: dict = Depends(require_roles('admin'))):
    return {"message": "Admin access granted"}
```

## Troubleshooting

### Common Issues

**1. Token Validation Fails**
```bash
# Verify token is not expired
echo $TOKEN | cut -d. -f2 | base64 -d | jq '.exp'
date +%s  # Compare with current timestamp

# Check issuer matches
echo $TOKEN | cut -d. -f2 | base64 -d | jq '.iss'
```

**2. CORS Issues**
- Add your application URL to Web Origins in Keycloak client settings
- Ensure Valid Redirect URIs include your callback URL

**3. Invalid Client Credentials**
```bash
# Test credentials
curl -v -X POST "${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "grant_type=client_credentials"
```

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth 2.0 Playground](https://www.oauth.com/playground/)
- [JWT.io Debugger](https://jwt.io/)
- [OpenID Connect Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html)

## Well-Known Endpoints

Keycloak exposes OpenID Connect discovery endpoint:

```bash
curl ${KEYCLOAK_URL}/realms/${REALM}/.well-known/openid-configuration | jq
```

This returns all available endpoints including:
- `authorization_endpoint`
- `token_endpoint`
- `userinfo_endpoint`
- `jwks_uri`
- `end_session_endpoint`
