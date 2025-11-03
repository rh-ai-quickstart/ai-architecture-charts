# Keycloak Integration Guide for Applications

A comprehensive guide for integrating Keycloak authentication in your applications, using the Spending Transaction Monitor as a reference implementation.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Authentication Flow](#authentication-flow)
- [Frontend Integration (React)](#frontend-integration-react)
- [Backend Integration (Python/FastAPI)](#backend-integration-python-fastapi)
- [Configuration](#configuration)
- [Protected Resources](#protected-resources)
- [User Profile Management](#user-profile-management)
- [User ID Mapping](#user-id-mapping-critical)
- [Role-Based Access Control](#role-based-access-control)
- [User Registration](#user-registration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Browser   │◄───────►│   Keycloak   │         │  Backend    │
│  (React)    │  OAuth2 │   Server     │         │  (FastAPI)  │
└──────┬──────┘  OIDC   └──────┬───────┘         └──────┬──────┘
       │                        │                        │
       │  1. Login Redirect     │                        │
       ├───────────────────────►│                        │
       │                        │                        │
       │  2. Auth Code          │                        │
       │◄───────────────────────┤                        │
       │                        │                        │
       │  3. Exchange for Token │                        │
       ├───────────────────────►│                        │
       │                        │                        │
       │  4. Access Token + ID Token                     │
       │◄───────────────────────┤                        │
       │                        │                        │
       │  5. API Request + Bearer Token                  │
       ├────────────────────────────────────────────────►│
       │                        │                        │
       │                        │  6. Validate Token     │
       │                        │◄───────────────────────┤
       │                        │     (JWKS)             │
       │                        │                        │
       │                        │  7. Return JWKS        │
       │                        ├───────────────────────►│
       │                        │                        │
       │  8. API Response (with user data)               │
       │◄────────────────────────────────────────────────┤
       │                        │                        │
```

### Key Components

1. **Keycloak Server**: Identity Provider (IdP) and Authorization Server
2. **Frontend (React)**: Public client using Authorization Code Flow with PKCE
3. **Backend (FastAPI)**: Resource server validating JWT tokens
4. **Database**: User data storage with Keycloak ID mapping

---

## Authentication Flow

### Detailed Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant React as React App
    participant KC as Keycloak
    participant API as FastAPI Backend
    participant DB as Database

    Note over User,DB: 1. Initial Authentication
    User->>React: Access protected route
    React->>React: Check auth state
    React->>User: Redirect to login
    User->>KC: Navigate to Keycloak login
    User->>KC: Enter credentials
    KC->>KC: Validate credentials
    KC->>React: Redirect with auth code
    React->>KC: Exchange code for tokens (PKCE)
    KC->>React: Return access_token + id_token + refresh_token
    React->>React: Store tokens (memory/localStorage)
    React->>React: Update auth state

    Note over User,DB: 2. Accessing Protected Resources
    User->>React: Click on feature
    React->>API: GET /users/profile<br/>Authorization: Bearer {access_token}
    API->>API: Extract Bearer token
    API->>KC: GET /.well-known/openid-configuration
    KC->>API: Return OIDC configuration
    API->>KC: GET /protocol/openid-connect/certs (JWKS)
    KC->>API: Return public keys
    API->>API: Validate JWT signature<br/>Verify issuer, audience, expiry
    API->>API: Extract claims (sub, email, roles)
    API->>DB: SELECT * FROM users WHERE keycloak_id = {sub}
    DB->>API: Return user record
    API->>API: Attach user context to request
    API->>API: Check authorization (roles)
    API->>DB: Execute business logic query
    DB->>API: Return data
    API->>React: 200 OK {user_profile}
    React->>User: Display profile

    Note over User,DB: 3. Token Refresh
    React->>React: Token near expiry
    React->>KC: POST /token<br/>grant_type=refresh_token
    KC->>React: New access_token
    React->>React: Update stored token

    Note over User,DB: 4. Logout
    User->>React: Click logout
    React->>KC: GET /logout
    KC->>KC: Invalidate session
    KC->>React: Redirect to post_logout_redirect_uri
    React->>React: Clear tokens and state
    React->>User: Show logged out state
```

---

## Frontend Integration (React)

### Dependencies

```json
{
  "dependencies": {
    "react": "^19.1.1",
    "react-oidc-context": "^3.3.0"
  }
}
```

### Installation

```bash
npm install react-oidc-context
# or
pnpm add react-oidc-context
```

### Configuration

```typescript
// src/config/auth.ts
export interface AuthConfig {
  environment: 'development' | 'production';
  bypassAuth: boolean;
  keycloak: {
    authority: string;        // Keycloak realm URL
    clientId: string;          // Client ID from Keycloak
    redirectUri: string;       // Your app's callback URL
    postLogoutRedirectUri: string;  // Where to go after logout
  };
}

export const authConfig: AuthConfig = {
  environment: import.meta.env.VITE_ENVIRONMENT || 'development',
  bypassAuth: import.meta.env.VITE_BYPASS_AUTH === 'true',
  keycloak: {
    // Auto-discovery URL format: {baseUrl}/realms/{realm-name}
    authority: import.meta.env.VITE_KEYCLOAK_URL || 
      'https://keycloak.example.com/realms/ai-platform',
    clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 
      'ai-platform-client',
    redirectUri: import.meta.env.VITE_KEYCLOAK_REDIRECT_URI ||
      window.location.origin,
    postLogoutRedirectUri: import.meta.env.VITE_KEYCLOAK_POST_LOGOUT_REDIRECT_URI ||
      window.location.origin,
  },
};
```

### Auth Provider Setup

```typescript
// src/contexts/AuthContext.tsx
import React, { createContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  AuthProvider as OIDCProvider,
  useAuth as useOIDCAuth,
} from 'react-oidc-context';
import { authConfig } from '../config/auth';

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Production OIDC Auth Provider
 */
export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const oidcConfig = useMemo(
    () => ({
      authority: authConfig.keycloak.authority,
      client_id: authConfig.keycloak.clientId,
      redirect_uri: authConfig.keycloak.redirectUri,
      post_logout_redirect_uri: authConfig.keycloak.postLogoutRedirectUri,
      
      // OAuth 2.0 settings
      response_type: 'code',  // Authorization Code Flow
      scope: 'openid profile email',  // Requested scopes
      
      // Token management
      automaticSilentRenew: true,  // Auto-refresh tokens
      loadUserInfo: false,  // Use ID token claims instead
      monitorSession: true,  // Monitor Keycloak session
      
      // Storage
      storeUser: true,  // Persist user in localStorage
    }),
    [],
  );

  return (
    <OIDCProvider {...oidcConfig}>
      <OIDCAuthWrapper>{children}</OIDCAuthWrapper>
    </OIDCProvider>
  );
};

/**
 * Wrapper to adapt OIDC provider to custom auth context
 */
const OIDCAuthWrapper = ({ children }: { children: React.ReactNode }) => {
  const oidcAuth = useOIDCAuth();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (oidcAuth.error) {
      console.error('OIDC Authentication Error:', oidcAuth.error);
    }

    if (oidcAuth.user) {
      // Extract user info from token claims
      const newUser: User = {
        id: oidcAuth.user.profile.sub!,  // Subject (Keycloak user ID)
        email: oidcAuth.user.profile.email!,
        username: oidcAuth.user.profile.preferred_username,
        name: oidcAuth.user.profile.name,
        // Extract realm roles from token
        roles: oidcAuth.user.profile.realm_access?.roles || ['user'],
      };
      setUser(newUser);

      // Pass access token to API client
      if (oidcAuth.user.access_token) {
        ApiClient.setToken(oidcAuth.user.access_token);
      }
    } else {
      setUser(null);
      ApiClient.setToken(null);
    }
  }, [oidcAuth.user, oidcAuth.error]);

  const login = useCallback(() => oidcAuth.signinRedirect(), [oidcAuth]);
  const logout = useCallback(() => oidcAuth.signoutRedirect(), [oidcAuth]);

  const contextValue: AuthContextType = {
    user,
    isAuthenticated: !!oidcAuth.user,
    isLoading: oidcAuth.isLoading,
    login,
    logout,
    error: oidcAuth.error ? new Error(oidcAuth.error.message) : null,
  };

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};
```

### API Client with Token Management

```typescript
// src/services/apiClient.ts
export class ApiClient {
  private static token: string | null = null;
  private static baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  static setToken(token: string | null) {
    this.token = token;
  }

  static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add Bearer token if available
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      // Token expired or invalid - trigger re-authentication
      // This will be caught by the auth provider
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  static get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  static post<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}
```

### Protecting Routes

```typescript
// src/components/ProtectedRoute.tsx
import { useAuth } from '../hooks/useAuth';
import { Navigate } from '@tanstack/react-router';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
}
```

### Using Authentication in Components

```typescript
// src/pages/Dashboard.tsx
import { useAuth } from '../hooks/useAuth';

export function Dashboard() {
  const { user, isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  return (
    <div>
      <h1>Welcome, {user?.name}</h1>
      <p>Email: {user?.email}</p>
      <p>Roles: {user?.roles.join(', ')}</p>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

---

## Backend Integration (Python/FastAPI)

### Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "python-jose[cryptography]>=3.3.0",  # JWT validation
    "httpx>=0.25.0",  # HTTP client for Keycloak
    "sqlalchemy>=2.0.0",  # Database ORM
]
```

### Installation

```bash
pip install fastapi python-jose[cryptography] httpx sqlalchemy
# or
uv add fastapi python-jose[cryptography] httpx sqlalchemy
```

### JWT Validation Middleware

```python
# src/auth/middleware.py
import logging
from typing import Dict, Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

class KeycloakJWTBearer:
    """JWT Bearer token validator for Keycloak using python-jose"""
    
    def __init__(self):
        # Keycloak configuration from environment
        self.keycloak_url = os.getenv('KEYCLOAK_URL', 'http://localhost:8080')
        self.realm = os.getenv('KEYCLOAK_REALM', 'ai-platform')
        self.client_id = os.getenv('KEYCLOAK_CLIENT_ID', 'ai-platform-client')
        
        # Build OIDC discovery URL
        self.oidc_discovery_url = f"{self.keycloak_url}/realms/{self.realm}/.well-known/openid-configuration"
        
        # Caching
        self._oidc_config = None
        self._jwks = None
        self._cache_time = 0
        self._cache_ttl = 3600  # 1 hour
    
    async def get_oidc_config(self) -> dict:
        """Fetch OIDC configuration from Keycloak (with caching)"""
        current_time = time.time()
        
        if self._oidc_config and (current_time - self._cache_time) < self._cache_ttl:
            return self._oidc_config
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.oidc_discovery_url, timeout=10)
                response.raise_for_status()
                self._oidc_config = response.json()
                self._cache_time = current_time
                logger.info(f"✅ Fetched OIDC config from {self.oidc_discovery_url}")
                return self._oidc_config
        except Exception as e:
            logger.error(f"❌ Failed to fetch OIDC config: {e}")
            raise HTTPException(
                status_code=503,
                detail='Authentication service unavailable'
            ) from e
    
    async def get_jwks(self) -> dict:
        """Fetch JWKS (JSON Web Key Set) from Keycloak"""
        oidc_config = await self.get_oidc_config()
        jwks_uri = oidc_config.get('jwks_uri')
        
        if not jwks_uri:
            raise HTTPException(status_code=500, detail='JWKS URI not found')
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri, timeout=10)
                response.raise_for_status()
                self._jwks = response.json()
                logger.info(f"✅ Fetched JWKS from {jwks_uri}")
                return self._jwks
        except Exception as e:
            logger.error(f"❌ Failed to fetch JWKS: {e}")
            raise HTTPException(
                status_code=503,
                detail='Authentication service unavailable'
            ) from e
    
    async def validate_token(self, token: str) -> dict:
        """
        Validate JWT token and return claims using python-jose
        
        Returns:
            dict: Token claims including sub, email, preferred_username, realm_access
        
        Raises:
            HTTPException: If token is invalid or expired
        """
        logger.info(f'🔍 Validating JWT token (length: {len(token)})')
        
        try:
            # Get OIDC config and JWKS
            oidc_config = await self.get_oidc_config()
            jwks = await self.get_jwks()
            
            # Decode and validate token
            claims = jwt.decode(
                token,
                jwks,
                algorithms=['RS256'],  # Keycloak uses RS256
                issuer=oidc_config['issuer'],
                options={
                    'verify_exp': True,  # Verify expiration
                    'verify_aud': False,  # Manually verify audience (see below)
                },
            )
            
            # Manual audience verification (more flexible for public clients)
            if 'aud' in claims:
                audience = claims.get('aud')
                valid_audiences = [self.client_id, 'account']
                audience_list = [audience] if isinstance(audience, str) else audience
                
                if not any(aud in valid_audiences for aud in audience_list):
                    logger.error(f'❌ Invalid audience: {audience}')
                    raise JWTError('Invalid audience')
            
            logger.info('✅ Token validation successful')
            logger.info(f'   Subject: {claims.get("sub")}')
            logger.info(f'   Email: {claims.get("email")}')
            logger.info(f'   Roles: {claims.get("realm_access", {}).get("roles", [])}')
            
            return claims
        
        except JWTError as e:
            logger.error(f'❌ JWT validation error: {e}')
            raise HTTPException(status_code=401, detail='Invalid token') from e
        except Exception as e:
            logger.error(f'❌ Token validation error: {e}')
            raise HTTPException(
                status_code=401,
                detail='Token validation failed'
            ) from e

# Global instance
keycloak_jwt = KeycloakJWTBearer()
```

### Authentication Dependencies

```python
# src/auth/middleware.py (continued)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import User

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Extract user info from JWT token (optional - returns None if no token)
    
    ⚠️  CRITICAL: User ID Mapping
    This function handles the mapping between Keycloak user ID (sub claim)
    and your application's database user ID.
    """
    if not credentials:
        return None
    
    # Validate token and get claims
    claims = await keycloak_jwt.validate_token(credentials.credentials)
    
    # Get Keycloak user ID from 'sub' claim
    keycloak_id = claims.get('sub')
    user_email = claims.get('email')
    
    # ⚠️  USER ID MAPPING - IMPORTANT!
    # By default, use Keycloak ID as user_id
    user_id = keycloak_id
    
    # If your app has existing users, map Keycloak ID to app user ID
    if session and keycloak_id:
        try:
            # Primary lookup: by keycloak_id (fast, recommended)
            result = await session.execute(
                select(User).where(User.keycloak_id == keycloak_id)
            )
            db_user = result.scalar_one_or_none()
            
            if db_user:
                user_id = db_user.id  # Use app's internal user ID
                logger.info(f'✅ Mapped Keycloak ID to app user: {user_id}')
            elif user_email:
                # Fallback: lookup by email and update keycloak_id
                result = await session.execute(
                    select(User).where(User.email == user_email)
                )
                db_user = result.scalar_one_or_none()
                
                if db_user:
                    # Link Keycloak ID to existing user
                    db_user.keycloak_id = keycloak_id
                    await session.commit()
                    user_id = db_user.id
                    logger.info(f'✅ Linked Keycloak ID to existing user: {user_id}')
        
        except Exception as e:
            logger.warning(f'⚠️  Database lookup failed: {e}')
            # Fall back to Keycloak ID
    
    return {
        'id': user_id,  # App user ID (mapped from Keycloak)
        'email': claims.get('email'),
        'username': claims.get('preferred_username'),
        'name': claims.get('name'),
        'roles': claims.get('realm_access', {}).get('roles', []),
        'keycloak_id': keycloak_id,  # Original Keycloak ID
        'token_claims': claims,  # Full token claims
    }


async def require_authentication(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Require valid JWT token (raises 401 if missing or invalid)"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail='Authentication required',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    
    return await get_current_user(credentials, session)


def require_role(required_role: str):
    """Dependency factory to require specific role"""
    async def check_role(current_user: dict = Depends(require_authentication)) -> dict:
        user_roles = current_user.get('roles', [])
        if required_role not in user_roles:
            raise HTTPException(
                status_code=403,
                detail=f'Required role: {required_role}'
            )
        return current_user
    return check_role


# Convenience dependencies
require_admin = require_role('admin')
require_user = require_role('user')
```

### Protecting API Endpoints

```python
# src/routes/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from auth.middleware import (
    get_current_user,
    require_authentication,
    require_admin,
)

router = APIRouter(prefix='/users', tags=['users'])

@router.get('/profile')
async def get_current_user_profile(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),  # ✅ Protected
):
    """
    Get the current logged-in user profile
    
    This endpoint demonstrates:
    1. How to protect an endpoint with authentication
    2. How to access the current user's information
    3. How to query user-specific data from the database
    """
    # current_user contains validated token claims
    user_id = current_user['id']  # App's internal user ID
    
    # Query database for user details
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'keycloak_id': user.keycloak_id,  # For reference
        # ... other user fields
    }


@router.get('/')
async def list_users(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),  # ✅ Admin only
):
    """List all users (admin only)"""
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users


@router.get('/{user_id}')
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_authentication),
):
    """Get specific user (with authorization check)"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    
    # Authorization: Users can only access their own data, admins can access any
    if ('admin' not in current_user.get('roles', []) and 
        current_user['id'] != user_id):
        raise HTTPException(status_code=403, detail='Access denied')
    
    return user
```

---

## Configuration

### Required Environment Variables

#### Frontend (.env)

```bash
# Keycloak Configuration
VITE_KEYCLOAK_URL=https://keycloak.example.com/realms/ai-platform
VITE_KEYCLOAK_CLIENT_ID=ai-platform-client
VITE_KEYCLOAK_REDIRECT_URI=https://app.example.com
VITE_KEYCLOAK_POST_LOGOUT_REDIRECT_URI=https://app.example.com

# API Configuration
VITE_API_BASE_URL=https://api.example.com

# Optional: Development bypass
VITE_BYPASS_AUTH=false
VITE_ENVIRONMENT=production
```

#### Backend (.env)

```bash
# Keycloak Configuration
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=ai-platform
KEYCLOAK_CLIENT_ID=ai-platform-client

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/myapp

# Optional: Development bypass
BYPASS_AUTH=false
ENVIRONMENT=production
```

### Keycloak OIDC Auto-Discovery URL

The OIDC discovery document is automatically available at:

```
{KEYCLOAK_URL}/realms/{REALM}/.well-known/openid-configuration
```

**Example:**
```
https://keycloak.example.com/realms/ai-platform/.well-known/openid-configuration
```

This URL provides:
- `issuer`: Token issuer
- `authorization_endpoint`: OAuth authorization URL
- `token_endpoint`: Token exchange URL
- `jwks_uri`: Public keys for JWT validation
- `userinfo_endpoint`: User info endpoint
- `end_session_endpoint`: Logout URL

### Keycloak Client Configuration

In Keycloak Admin Console, configure your client:

1. **Client ID**: `ai-platform-client`
2. **Client Type**: `OpenID Connect`
3. **Client authentication**: `Off` (public client for frontend)
4. **Authorization**: `Off`
5. **Standard flow**: `Enabled` (Authorization Code Flow)
6. **Direct access grants**: `Enabled` (for testing)
7. **Valid redirect URIs**: 
   - `https://app.example.com/*`
   - `http://localhost:3000/*` (for development)
8. **Valid post logout redirect URIs**: Same as redirect URIs
9. **Web origins**: 
   - `https://app.example.com`
   - `http://localhost:3000` (for development)

---

## Protected Resources

### Frontend Route Protection

```typescript
// src/router.tsx
import { createRoute } from '@tanstack/react-router';
import { ProtectedRoute } from './components/ProtectedRoute';

export const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: () => (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  ),
});

// Public routes (no protection)
export const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: LoginPage,
});
```

### Backend Endpoint Protection Patterns

```python
# Pattern 1: Optional authentication (returns None if not authenticated)
@router.get('/public-data')
async def get_public_data(
    current_user: dict = Depends(get_current_user),  # Optional
):
    """Endpoint accessible to both authenticated and anonymous users"""
    if current_user:
        # Personalized data
        return {'message': f'Hello {current_user["email"]}'}
    else:
        # Generic data
        return {'message': 'Hello anonymous user'}


# Pattern 2: Required authentication
@router.get('/protected-data')
async def get_protected_data(
    current_user: dict = Depends(require_authentication),  # Required
):
    """Endpoint requires valid JWT token"""
    return {'data': 'secret', 'user': current_user['email']}


# Pattern 3: Role-based access
@router.get('/admin-only')
async def admin_endpoint(
    current_user: dict = Depends(require_admin),  # Admin role required
):
    """Endpoint requires admin role"""
    return {'admin_data': 'sensitive information'}


# Pattern 4: Custom authorization logic
@router.get('/resource/{resource_id}')
async def get_resource(
    resource_id: str,
    current_user: dict = Depends(require_authentication),
    session: AsyncSession = Depends(get_db),
):
    """Endpoint with custom authorization logic"""
    resource = await get_resource_by_id(session, resource_id)
    
    # Check if user owns the resource
    if resource.owner_id != current_user['id'] and 'admin' not in current_user['roles']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    return resource
```

---

## User Profile Management

### Frontend: Fetching User Profile

```typescript
// src/hooks/useCurrentUser.ts
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../services/apiClient';

export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  keycloak_id: string;
  is_active: boolean;
  created_at: string;
  // ... other fields
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => ApiClient.get<UserProfile>('/users/profile'),
    enabled: true,  // Only fetch if authenticated
    staleTime: 5 * 60 * 1000,  // Cache for 5 minutes
  });
}
```

```typescript
// src/pages/Profile.tsx
import { useCurrentUser } from '../hooks/useCurrentUser';

export function ProfilePage() {
  const { data: user, isLoading, error } = useCurrentUser();

  if (isLoading) return <div>Loading profile...</div>;
  if (error) return <div>Error loading profile: {error.message}</div>;

  return (
    <div>
      <h1>My Profile</h1>
      <p>Email: {user?.email}</p>
      <p>Name: {user?.first_name} {user?.last_name}</p>
      <p>Keycloak ID: {user?.keycloak_id}</p>
    </div>
  );
}
```

### Backend: User Profile Endpoint

Already shown above in the "Protecting API Endpoints" section.

---

## User ID Mapping (CRITICAL!)

### The Problem

When integrating Keycloak with an existing application that has its own users table, you face a **user ID mismatch** problem:

- **Keycloak** assigns its own user IDs (UUID format, e.g., `a1b2c3d4-...`)
- **Your app** may have existing user IDs (integer, UUID, or other format)
- **Foreign keys** in your database reference your app's user IDs, not Keycloak's

### The Solution: keycloak_id Column

Add a `keycloak_id` column to your users table to map between the two ID systems.

#### Database Migration

```python
# alembic/versions/xxx_add_keycloak_id.py
def upgrade():
    op.add_column('users', sa.Column('keycloak_id', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_keycloak_id', 'users', ['keycloak_id'])
    op.create_index('ix_users_keycloak_id', 'users', ['keycloak_id'])

def downgrade():
    op.drop_index('ix_users_keycloak_id')
    op.drop_constraint('uq_users_keycloak_id', 'users')
    op.drop_column('users', 'keycloak_id')
```

#### Database Model

```python
# db/models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)  # App's internal ID
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    keycloak_id: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
        index=True,  # Index for fast lookups
    )
    first_name: Mapped[str]
    last_name: Mapped[str]
    # ... other fields
```

#### User Lookup Strategy

The middleware (shown earlier) implements a **three-tier lookup strategy**:

1. **Primary**: Lookup by `keycloak_id` (fast, indexed)
2. **Fallback**: If not found, lookup by email
3. **Auto-link**: If found by email, update `keycloak_id` for future fast lookups
4. **Default**: If neither found, use Keycloak ID as user_id

This strategy ensures:
- ✅ Existing users are automatically linked to Keycloak
- ✅ New users work immediately
- ✅ Performance improves over time as mappings are created
- ✅ No manual user migration required

### Migration Workflow

```mermaid
graph TD
    A[User logs in with Keycloak] --> B{keycloak_id exists?}
    B -->|Yes| C[Fast lookup by keycloak_id]
    C --> D[Use app user ID]
    B -->|No| E[Lookup by email]
    E --> F{User found?}
    F -->|Yes| G[Update keycloak_id]
    G --> H[Link accounts]
    H --> D
    F -->|No| I[Create new user<br/>or use Keycloak ID]
    I --> D
    D --> J[Return user context]
```

---

## Role-Based Access Control

### Keycloak Realm Roles

In Keycloak Admin Console:

1. Navigate to: Realm → Roles
2. Create roles:
   - `admin` - Full access
   - `user` - Standard user access
   - `viewer` - Read-only access
   - Custom roles as needed

### Assign Roles to Users

1. Navigate to: Users → Select User → Role mapping
2. Assign realm roles

### Extract Roles from Token

Roles are included in the JWT token under `realm_access.roles`:

```json
{
  "sub": "a1b2c3d4-...",
  "email": "user@example.com",
  "realm_access": {
    "roles": ["user", "admin"]
  }
}
```

### Frontend: Role-Based UI

```typescript
// src/hooks/useAuth.ts
export function useAuth() {
  const { user } = useContext(AuthContext);
  
  const hasRole = (role: string) => {
    return user?.roles.includes(role) || false;
  };
  
  const isAdmin = () => hasRole('admin');
  
  return {
    user,
    hasRole,
    isAdmin,
    // ... other auth functions
  };
}
```

```typescript
// src/components/AdminPanel.tsx
import { useAuth } from '../hooks/useAuth';

export function AdminPanel() {
  const { isAdmin } = useAuth();

  if (!isAdmin()) {
    return <div>Access denied. Admin privileges required.</div>;
  }

  return <div>Admin content here</div>;
}
```

### Backend: Role-Based Endpoints

Already shown in the "Authentication Dependencies" section with `require_role` factory.

### Client Roles (Advanced)

For more granular permissions, use **client roles**:

1. In Keycloak: Clients → {your-client} → Roles
2. Create client-specific roles
3. Assign to users
4. Extract from token under `resource_access.{client_id}.roles`

```python
# Extract client roles
def get_client_roles(claims: dict, client_id: str) -> list[str]:
    return (
        claims.get('resource_access', {})
        .get(client_id, {})
        .get('roles', [])
    )
```

---

## User Registration

### ⚠️ Not Implemented in Spending Transaction Monitor

User registration was not implemented in the reference project, but here's how to add it:

### Option 1: Keycloak Self-Registration (Recommended)

Enable self-registration in Keycloak:

1. **Keycloak Admin Console**:
   - Realm Settings → Login → User registration: `On`
   - Configure email verification
   - Set up email server (SMTP)

2. **Registration Flow**:
   ```
   User → Click "Register" → Keycloak registration form → 
   Email verification → Account created → Auto-login
   ```

3. **Sync to App Database**:
   - Create a webhook or scheduled job to sync new Keycloak users to your app database
   - Or create users on first login (lazy creation)

### Option 2: Custom Registration API

Implement registration in your backend:

```python
# src/routes/auth.py
from keycloak import KeycloakAdmin

keycloak_admin = KeycloakAdmin(
    server_url=settings.KEYCLOAK_URL,
    realm_name=settings.KEYCLOAK_REALM,
    client_id=settings.KEYCLOAK_CLIENT_ID,
    client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
    verify=True,
)

@router.post('/register')
async def register_user(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    session: AsyncSession = Depends(get_db),
):
    """Register a new user in both Keycloak and app database"""
    try:
        # 1. Create user in Keycloak
        keycloak_user_id = keycloak_admin.create_user({
            'email': email,
            'username': email,
            'enabled': True,
            'firstName': first_name,
            'lastName': last_name,
            'credentials': [{
                'type': 'password',
                'value': password,
                'temporary': False,
            }],
            'emailVerified': False,  # Require email verification
        })
        
        # 2. Send verification email
        keycloak_admin.send_verify_email(keycloak_user_id)
        
        # 3. Create user in app database
        new_user = User(
            email=email,
            keycloak_id=keycloak_user_id,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(new_user)
        await session.commit()
        
        return {
            'message': 'User created. Please check your email for verification.',
            'user_id': new_user.id,
        }
    
    except Exception as e:
        logger.error(f'Registration failed: {e}')
        raise HTTPException(status_code=400, detail=str(e))
```

### Option 3: Lazy User Creation

Create users in your app database on first login:

```python
async def get_current_user(...):
    claims = await keycloak_jwt.validate_token(...)
    keycloak_id = claims.get('sub')
    
    # Try to find existing user
    result = await session.execute(
        select(User).where(User.keycloak_id == keycloak_id)
    )
    db_user = result.scalar_one_or_none()
    
    # If user doesn't exist, create them
    if not db_user:
        db_user = User(
            keycloak_id=keycloak_id,
            email=claims.get('email'),
            first_name=claims.get('given_name', ''),
            last_name=claims.get('family_name', ''),
        )
        session.add(db_user)
        await session.commit()
        logger.info(f'✨ Created new user from Keycloak: {db_user.email}')
    
    return {
        'id': db_user.id,
        # ... other fields
    }
```

---

## Best Practices

### Security

1. **✅ Use HTTPS in Production**
   - Always use TLS for Keycloak and your application
   - Never send tokens over unencrypted connections

2. **✅ Validate Tokens Properly**
   - Verify signature using JWKS
   - Check issuer, audience, and expiration
   - Use established libraries (python-jose, react-oidc-context)

3. **✅ Store Tokens Securely**
   - Frontend: Memory or localStorage (not cookies for public clients)
   - Backend: Never store access tokens (validate on each request)
   - Use refresh tokens for long sessions

4. **✅ Implement Token Refresh**
   - Refresh tokens before they expire
   - Handle token refresh failures gracefully

5. **✅ Use Short Token Lifespans**
   - Access tokens: 5-15 minutes
   - Refresh tokens: Hours to days
   - Adjust based on security requirements

6. **✅ Validate Audience**
   - Ensure tokens are intended for your client

7. **✅ Protect Against CSRF**
   - Use state parameter in OAuth flow
   - Implement PKCE for public clients

### Performance

1. **✅ Cache OIDC Configuration**
   - Cache discovery document and JWKS
   - Refresh periodically (e.g., 1 hour)

2. **✅ Index keycloak_id Column**
   - Fast user lookups
   - Essential for performance at scale

3. **✅ Avoid User Info Endpoint**
   - Use claims from ID token instead
   - Reduces network requests

4. **✅ Implement Connection Pooling**
   - Reuse HTTP connections to Keycloak
   - Use async HTTP clients (httpx, aiohttp)

### User Experience

1. **✅ Handle Auth Errors Gracefully**
   - Show user-friendly error messages
   - Provide clear login instructions

2. **✅ Implement Silent Authentication**
   - Automatic token refresh
   - Seamless re-authentication when possible

3. **✅ Remember User Session**
   - Persist auth state across page reloads
   - Use localStorage or sessionStorage

4. **✅ Provide Logout Functionality**
   - Clear local state
   - Redirect to Keycloak logout
   - Invalidate backend sessions

### Development

1. **✅ Use Auth Bypass for Development**
   - Toggle authentication with environment variable
   - Speeds up local development
   - Never enable in production

2. **✅ Test with Multiple Users**
   - Create test users with different roles
   - Test authorization logic thoroughly

3. **✅ Log Auth Events**
   - Log successful/failed authentications
   - Track token validation
   - Monitor for suspicious activity

4. **✅ Document Required Secrets**
   - Clearly document all environment variables
   - Provide example configurations

---

## Troubleshooting

### Common Issues

#### 1. "Invalid issuer" Error

**Problem**: Token issuer doesn't match expected issuer.

**Solution**:
- Check `KEYCLOAK_URL` matches exactly (including protocol and realm)
- Verify Keycloak is accessible from backend
- Check for trailing slashes in URLs

```bash
# Test OIDC discovery
curl https://keycloak.example.com/realms/ai-platform/.well-known/openid-configuration
```

#### 2. "CORS Error" in Frontend

**Problem**: Keycloak blocks requests from your frontend origin.

**Solution**:
- Add your frontend URL to "Web Origins" in Keycloak client settings
- Use wildcards for development: `http://localhost:*`

#### 3. Token Validation Fails

**Problem**: Backend rejects valid tokens.

**Solution**:
- Check clock synchronization (token exp claim)
- Verify JWKS is fetched correctly
- Check audience claim matches client ID
- Enable debug logging

```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
```

#### 4. User Not Found After Login

**Problem**: User exists in Keycloak but not in app database.

**Solution**:
- Implement lazy user creation (shown above)
- Or sync users from Keycloak to database
- Check `keycloak_id` mapping logic

#### 5. Infinite Redirect Loop

**Problem**: Frontend keeps redirecting to login.

**Solution**:
- Check redirect URIs in Keycloak client settings
- Verify token is being stored correctly
- Check browser localStorage/cookies
- Ensure `isAuthenticated` state updates properly

#### 6. "403 Forbidden" on Protected Endpoints

**Problem**: User is authenticated but doesn't have required role.

**Solution**:
- Verify roles are assigned in Keycloak
- Check role extraction from token
- Confirm role names match exactly (case-sensitive)

### Debug Checklist

```bash
# 1. Test Keycloak connectivity
curl https://keycloak.example.com/realms/ai-platform/.well-known/openid-configuration

# 2. Verify JWKS endpoint
curl https://keycloak.example.com/realms/ai-platform/protocol/openid-connect/certs

# 3. Test token endpoint (get access token)
curl -X POST https://keycloak.example.com/realms/ai-platform/protocol/openid-connect/token \
  -d "client_id=ai-platform-client" \
  -d "username=testuser" \
  -d "password=testpass" \
  -d "grant_type=password"

# 4. Decode JWT token (paste token at jwt.io)
echo $TOKEN | jwt decode -

# 5. Test API endpoint with token
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/users/profile
```

---

## Summary

### Required Steps for Integration

1. **Keycloak Setup**:
   - ✅ Create realm
   - ✅ Create client (public, OIDC)
   - ✅ Configure redirect URIs
   - ✅ Create realm roles
   - ✅ Create test users

2. **Database**:
   - ✅ Add `keycloak_id` column to users table
   - ✅ Create unique index on `keycloak_id`
   - ✅ Implement user lookup logic

3. **Frontend**:
   - ✅ Install `react-oidc-context`
   - ✅ Configure OIDC provider
   - ✅ Implement auth context
   - ✅ Add Bearer token to API requests
   - ✅ Protect routes

4. **Backend**:
   - ✅ Install `python-jose`
   - ✅ Implement JWT validation
   - ✅ Create authentication dependencies
   - ✅ Protect endpoints
   - ✅ Implement role-based access control

5. **Configuration**:
   - ✅ Set environment variables
   - ✅ Configure CORS
   - ✅ Test auto-discovery URL

6. **Testing**:
   - ✅ Test authentication flow
   - ✅ Test protected endpoints
   - ✅ Test role-based access
   - ✅ Test user ID mapping

---

## Additional Resources

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [OpenID Connect Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [react-oidc-context](https://github.com/authts/react-oidc-context)
- [python-jose](https://github.com/mpdavis/python-jose)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/) - Debug JWT tokens

---

## Support

For questions or issues:
- Reference Implementation: [Spending Transaction Monitor](https://github.com/example/spending-transaction-monitor)
- Keycloak Helm Chart: See main README.md
- Community Support: Create an issue in the repository

---

**Last Updated**: 2025-01-03
**Tested With**: 
- Keycloak 26.0.7
- react-oidc-context 3.3.0
- python-jose 3.3.0
- FastAPI 0.104.0

