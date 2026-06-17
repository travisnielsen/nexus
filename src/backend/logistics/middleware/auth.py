"""
Azure AD Authentication Configuration

This module sets up Azure AD token validation for the FastAPI backend.
It validates JWT tokens issued by Azure AD and extracts user information.
"""

import logging

import jwt
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from jwt import PyJWKClient
from pydantic_settings import BaseSettings
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AzureADSettings(BaseSettings):
    """Azure AD configuration loaded from environment variables."""

    # The Application (client) ID of the Backend API app registration
    AZURE_AD_CLIENT_ID: str = ""

    # The Directory (tenant) ID
    AZURE_AD_TENANT_ID: str = ""

    # The Application ID URI of the Backend API app registration
    # Usually looks like: api://<backend-app-guid>
    AZURE_AD_API_SCOPE_URI: str = ""

    # Required scope name exposed by the Backend API app registration
    # Usually looks like: api://<backend-app-guid>/access_as_user
    AZURE_AD_API_SCOPE: str = "access_as_user"

    # Set to "true" to enable authentication (default in production)
    AUTH_ENABLED: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


# Load settings from environment
azure_ad_settings = AzureADSettings()


# Paths that don't require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/info",
    "/agent",
    "/agent/info",
    "/logistics/info",
    "/docs",
    "/openapi.json",
    "/redoc",
}


class AzureADAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates Azure AD JWT tokens on all requests.
    """

    def __init__(self, app, settings: AzureADSettings):
        super().__init__(app)
        self.settings = settings
        self.jwks_uri = (
            f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
        )
        self.jwks_client = PyJWKClient(self.jwks_uri) if settings.AZURE_AD_TENANT_ID else None

        # Azure AD accepted issuers
        # - v2.0 is preferred (requires accessTokenAcceptedVersion=2 in app manifest)
        # - v1.0 is also accepted until the app manifest is updated in Azure Portal
        # See: App registrations → Manifest → "accessTokenAcceptedVersion": 2
        self.valid_issuers = [
            f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0",
            f"https://sts.windows.net/{settings.AZURE_AD_TENANT_ID}/",
        ]

        # Parse full scope URI into audience + scope name.
        # Example: api://<backend-app-guid>/access_as_user
        scope_uri = settings.AZURE_AD_API_SCOPE_URI.strip()
        if scope_uri and "/" in scope_uri:
            audience, required_scope = scope_uri.rsplit("/", 1)
        else:
            audience = scope_uri or f"api://{settings.AZURE_AD_CLIENT_ID}"
            required_scope = settings.AZURE_AD_API_SCOPE

        self.valid_audience = audience
        self.required_scope = required_scope or settings.AZURE_AD_API_SCOPE

        logger.info(f"Azure AD Auth configured for issuers: {self.valid_issuers}")
        logger.info(f"Azure AD Auth configured for audience: {self.valid_audience}")
        logger.info(f"Azure AD Auth configured for scope: {self.required_scope}")

    async def dispatch(self, request: Request, call_next):
        # Normalize path by removing trailing slash for comparison
        path = request.url.path.rstrip("/") or "/"

        # Skip auth for public paths
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip if auth is explicitly disabled (AUTH_ENABLED=false)
        if not self.settings.AUTH_ENABLED:
            logger.warning("Authentication is DISABLED via AUTH_ENABLED=false environment variable")
            return await call_next(request)

        # Skip if auth is not configured
        if not self.settings.AZURE_AD_CLIENT_ID or not self.settings.AZURE_AD_TENANT_ID:
            logger.warning("Azure AD auth not configured, allowing request without validation")
            return await call_next(request)

        # Get the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing Authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract the token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid Authorization header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if the token looks like a JWT (should have 3 parts separated by dots)
        token_parts = token.split(".")
        if len(token_parts) != 3:
            logger.error(
                f"Token does not have 3 parts (has {len(token_parts)}). This is not a valid JWT."
            )
            # Log the length of each part to help debug
            for i, part in enumerate(token_parts):
                logger.error(
                    f"  Part {i}: length={len(part)}, preview={part[:20] if len(part) > 20 else part}..."
                )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": f"Invalid token format: expected JWT with 3 parts, got {len(token_parts)}"
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Validate the token
        try:
            if self.jwks_client is None:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "JWKS client not configured"},
                )

            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            last_error: Exception | None = None
            payload = None
            for issuer in self.valid_issuers:
                try:
                    payload = jwt.decode(
                        token,
                        signing_key.key,
                        algorithms=["RS256"],
                        audience=self.valid_audience,
                        issuer=issuer,
                    )
                    break
                except jwt.InvalidIssuerError as e:
                    last_error = e
            if payload is None:
                raise last_error or jwt.InvalidTokenError("No valid issuer matched")

            # Validate that the token contains the required scope
            # The scope claim in the token lists all permissions granted
            token_scopes = payload.get("scp", "").split()
            if self.required_scope not in token_scopes:
                logger.warning(
                    f"Token missing required scope '{self.required_scope}'. "
                    f"Token scopes: {token_scopes}"
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": f"Token does not have required scope: {self.required_scope}"
                    },
                )

            # Store user info in request state for downstream use
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token has expired"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.error(f"Token validation failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": f"Invalid token: {str(e)}"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Unexpected auth error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication error"},
            )

        return await call_next(request)


def get_azure_auth_scheme() -> SingleTenantAzureAuthorizationCodeBearer:
    """
    Create and return the Azure AD authentication scheme.

    This validates tokens and extracts claims from the JWT.
    Uses separate frontend and backend app registrations following Zero Trust principles.
    """
    # Use explicit full scope URI when provided, else derive from client ID + scope name.
    configured_scope_uri = azure_ad_settings.AZURE_AD_API_SCOPE_URI.strip()
    backend_scope_uri = configured_scope_uri or (
        f"api://{azure_ad_settings.AZURE_AD_CLIENT_ID}/{azure_ad_settings.AZURE_AD_API_SCOPE}"
    )

    return SingleTenantAzureAuthorizationCodeBearer(
        app_client_id=azure_ad_settings.AZURE_AD_CLIENT_ID,
        tenant_id=azure_ad_settings.AZURE_AD_TENANT_ID,
        scopes={
            # Define the scopes this Backend API exposes
            # The key is the fully qualified scope URI
            backend_scope_uri: "Access Backend API as user",
        }
        if azure_ad_settings.AZURE_AD_CLIENT_ID
        else {},
        # Allow token validation even if openapi docs aren't being used
        allow_guest_users=False,
    )


# Create the auth scheme instance
# This will be None if credentials aren't configured
azure_scheme = None
if azure_ad_settings.AZURE_AD_CLIENT_ID and azure_ad_settings.AZURE_AD_TENANT_ID:
    azure_scheme = get_azure_auth_scheme()
