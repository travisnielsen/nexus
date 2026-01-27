"""
Azure AD (Entra ID) Authentication for MCP Server

This module provides JWT token validation middleware for the Starlette-based MCP server.
It validates tokens issued by Azure AD/Entra ID and ensures only authenticated requests
can access protected endpoints.

Configuration via environment variables:
- AZURE_AD_TENANT_ID: The Azure AD tenant ID
- AZURE_AD_CLIENT_ID: The App Registration client ID (audience for the token)
- AUTH_ENABLED: Set to "true" to enable authentication (default: false)
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

import httpx
import jwt
from cachetools import TTLCache
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

AZURE_AD_TENANT_ID = os.getenv("AZURE_AD_TENANT_ID", "")
AZURE_AD_CLIENT_ID = os.getenv("AZURE_AD_CLIENT_ID", "")
AZURE_AD_APP_ID_URI = os.getenv("AZURE_AD_APP_ID_URI", "")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health",
    "/",
}

# Cache for JWKS keys (1 hour TTL, max 10 keys)
_jwks_cache: TTLCache = TTLCache(maxsize=10, ttl=3600)


# ============================================================================
# JWKS Fetching and Caching
# ============================================================================

def get_jwks_uri(tenant_id: str) -> str:
    """Get the JWKS URI for the given tenant."""
    return f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


def get_openid_config_uri(tenant_id: str) -> str:
    """Get the OpenID Connect configuration URI."""
    return f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"


def fetch_jwks(tenant_id: str) -> dict[str, Any]:
    """Fetch JWKS from Azure AD, with caching."""
    cache_key = f"jwks:{tenant_id}"
    
    if cache_key in _jwks_cache:
        return _jwks_cache[cache_key]
    
    jwks_uri = get_jwks_uri(tenant_id)
    logger.info(f"Fetching JWKS from {jwks_uri}")
    
    with httpx.Client(timeout=10.0) as client:
        response = client.get(jwks_uri)
        response.raise_for_status()
        jwks = response.json()
    
    _jwks_cache[cache_key] = jwks
    return jwks


def get_signing_key(token: str, tenant_id: str) -> dict[str, Any]:
    """Get the signing key for a JWT token from JWKS."""
    # Decode header without verification to get the key ID
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    
    if not kid:
        raise jwt.InvalidTokenError("Token header missing 'kid' claim")
    
    # Fetch JWKS and find the matching key
    jwks = fetch_jwks(tenant_id)
    
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    
    # Key not found - maybe JWKS was rotated, clear cache and retry
    cache_key = f"jwks:{tenant_id}"
    if cache_key in _jwks_cache:
        del _jwks_cache[cache_key]
        jwks = fetch_jwks(tenant_id)
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
    
    raise jwt.InvalidTokenError(f"Unable to find signing key with kid: {kid}")


# ============================================================================
# Token Validation
# ============================================================================

def validate_token(token: str) -> dict[str, Any]:
    """
    Validate a JWT token issued by Azure AD.
    
    Args:
        token: The JWT token to validate
        
    Returns:
        The decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If the token is invalid
    """
    if not AZURE_AD_TENANT_ID or not AZURE_AD_CLIENT_ID:
        raise jwt.InvalidTokenError("Azure AD not configured")
    
    # Get the signing key
    signing_key_data = get_signing_key(token, AZURE_AD_TENANT_ID)
    
    # Build the public key from JWK
    from jwt import algorithms
    public_key = algorithms.RSAAlgorithm.from_jwk(signing_key_data)
    
    # Valid issuers (v1.0 and v2.0 endpoints)
    valid_issuers = [
        f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}/v2.0",
        f"https://sts.windows.net/{AZURE_AD_TENANT_ID}/",
    ]
    
    # Valid audiences
    valid_audiences = [AZURE_AD_CLIENT_ID]
    if AZURE_AD_APP_ID_URI:
        valid_audiences.append(AZURE_AD_APP_ID_URI)
    else:
        # Default App ID URI format
        valid_audiences.append(f"api://{AZURE_AD_CLIENT_ID}")
    
    # Decode and validate the token
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=valid_audiences,
        issuer=valid_issuers,
        options={
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_aud": True,
            "verify_iss": True,
        },
    )
    
    return payload


# ============================================================================
# Starlette Middleware
# ============================================================================

class EntraIDAuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware for Azure AD (Entra ID) authentication.
    
    This middleware validates JWT tokens on incoming requests and rejects
    unauthenticated requests to protected endpoints.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Normalize path
        path = request.url.path.rstrip("/") or "/"
        
        # Skip auth for public paths
        if path in PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip if auth is not enabled
        if not AUTH_ENABLED:
            logger.debug("Authentication not enabled - allowing unauthenticated request")
            return await call_next(request)
        
        # Skip if not configured (but auth is enabled - log warning)
        if not AZURE_AD_TENANT_ID or not AZURE_AD_CLIENT_ID:
            logger.warning("AUTH_ENABLED=true but Azure AD not configured - allowing request without validation")
            return await call_next(request)
        
        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid scheme")
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid Authorization header format. Expected: Bearer <token>"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token
        try:
            payload = validate_token(token)
            # Store user info in request state
            request.state.user = payload
            request.state.user_id = payload.get("oid") or payload.get("sub")
            request.state.user_name = payload.get("name") or payload.get("preferred_username")
            
            # Log access info (single line: appid, upn, name)
            appid = payload.get("appid", "unknown")
            upn = payload.get("upn", payload.get("unique_name", "unknown"))
            name = payload.get("name", "unknown")
            logger.info(f"ACCESS: {request.method} {path} | app={appid} upn={upn} name={name}")
            
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content={"error": "Token has expired"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidAudienceError:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid token audience"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidIssuerError:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid token issuer"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Token validation failed: {e}")
            return JSONResponse(
                status_code=401,
                content={"error": f"Invalid token: {str(e)}"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected auth error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Authentication error"},
            )
        
        return await call_next(request)


def is_auth_enabled() -> bool:
    """Check if authentication is enabled and configured."""
    if not AUTH_ENABLED:
        return False
    if not AZURE_AD_TENANT_ID or not AZURE_AD_CLIENT_ID:
        return False
    return True


def get_auth_config() -> dict[str, Any]:
    """Get current authentication configuration (for debugging)."""
    return {
        "enabled": is_auth_enabled(),
        "auth_enabled_flag": AUTH_ENABLED,
        "tenant_id_configured": bool(AZURE_AD_TENANT_ID),
        "client_id_configured": bool(AZURE_AD_CLIENT_ID),
        "app_id_uri_configured": bool(AZURE_AD_APP_ID_URI),
    }
