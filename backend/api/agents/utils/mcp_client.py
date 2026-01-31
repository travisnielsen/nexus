"""
MCP Data Client for Logistics Backend.

This module provides a simple HTTP client for fetching flight data from the
Logistics MCP Server. It uses httpx to call the MCP server's REST API endpoints.

The MCP server exposes:
- /api/flights - Get filtered/paginated flights
- /api/flights/{flight_id} - Get a single flight
- /api/summary - Get flight summary statistics
- /api/historical - Get historical payload data with predictions
- /api/predictions - Get predicted payload data
- /api/routes - Get available routes with statistics

Configuration via environment variables:
- MCP_SERVER_URL: Base URL of the MCP server (default: http://localhost:8001)
- MCP_TIMEOUT: Request timeout in seconds (default: 10.0)
- MCP_CLIENT_ID: The client ID (audience) of the MCP server for token acquisition
- MCP_AUTH_ENABLED: Set to "true" to enable token acquisition (default: false)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# MCP server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT", "10.0"))
MCP_CLIENT_ID = os.getenv("MCP_CLIENT_ID", "")  # The MCP server's app registration client ID
MCP_AUTH_ENABLED = os.getenv("MCP_AUTH_ENABLED", "false").lower() == "true"

# Token cache (simple in-memory cache)
_token_cache: dict[str, Any] = {}


def get_mcp_server_url() -> str:
    """Get the MCP server base URL."""
    return MCP_SERVER_URL


def _get_mcp_token() -> str | None:
    """
    Get an access token for the MCP server using DefaultAzureCredential.
    
    Returns:
        The access token string, or None if auth is disabled or not configured.
    """
    if not MCP_AUTH_ENABLED:
        logger.debug("MCP authentication not enabled")
        return None
    
    if not MCP_CLIENT_ID:
        logger.debug("MCP_CLIENT_ID not configured, skipping token acquisition")
        return None
    
    try:
        from azure.identity import DefaultAzureCredential
        
        # Check cache first (simple cache, not checking expiry in detail)
        cache_key = f"token:{MCP_CLIENT_ID}"
        if cache_key in _token_cache:
            cached = _token_cache[cache_key]
            # Use cached token if it has more than 5 minutes until expiry
            import time
            if cached.get("expires_on", 0) > time.time() + 300:
                return cached.get("token")
        
        # Acquire new token
        credential = DefaultAzureCredential()
        # The scope should be the MCP server's App ID URI with /.default
        scope = f"api://{MCP_CLIENT_ID}/.default"
        token = credential.get_token(scope)
        
        # Cache the token
        _token_cache[cache_key] = {
            "token": token.token,
            "expires_on": token.expires_on,
        }
        
        logger.debug(f"Acquired MCP access token (expires: {token.expires_on})")
        return token.token
        
    except Exception as e:
        logger.warning(f"Failed to acquire MCP token: {e}")
        return None


def _get_auth_headers() -> dict[str, str]:
    """Get authorization headers for MCP requests."""
    token = _get_mcp_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


async def _get_mcp_token_async() -> str | None:
    """
    Async version: Get an access token for the MCP server.
    """
    if not MCP_AUTH_ENABLED:
        return None
    
    if not MCP_CLIENT_ID:
        return None
    
    try:
        from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
        import time
        
        # Check cache
        cache_key = f"token:{MCP_CLIENT_ID}"
        if cache_key in _token_cache:
            cached = _token_cache[cache_key]
            if cached.get("expires_on", 0) > time.time() + 300:
                return cached.get("token")
        
        # Acquire new token
        async with AsyncDefaultAzureCredential() as credential:
            scope = f"api://{MCP_CLIENT_ID}/.default"
            token = await credential.get_token(scope)
        
        # Cache the token
        _token_cache[cache_key] = {
            "token": token.token,
            "expires_on": token.expires_on,
        }
        
        return token.token
        
    except Exception as e:
        logger.warning(f"Failed to acquire MCP token (async): {e}")
        return None


async def _get_auth_headers_async() -> dict[str, str]:
    """Async version: Get authorization headers for MCP requests."""
    token = await _get_mcp_token_async()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# ============================================================================
# Async HTTP Client Functions
# ============================================================================

async def get_flights_from_mcp(
    limit: int = 100,
    offset: int = 0,
    risk_level: str | None = None,
    utilization: str | None = None,
    route_from: str | None = None,
    route_to: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "utilizationPercent",
    sort_desc: bool = True,
) -> dict[str, Any]:
    """Get flights from MCP server via HTTP."""
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "sort_desc": str(sort_desc).lower(),
    }
    if risk_level:
        params["risk_level"] = risk_level
    if utilization:
        params["utilization"] = utilization
    if route_from:
        params["route_from"] = route_from
    if route_to:
        params["route_to"] = route_to
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    
    headers = await _get_auth_headers_async()
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        response = await client.get(f"{MCP_SERVER_URL}/api/flights", params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_flight_by_id_from_mcp(flight_id: str) -> dict[str, Any]:
    """Get a single flight from MCP server via HTTP."""
    headers = await _get_auth_headers_async()
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        response = await client.get(f"{MCP_SERVER_URL}/api/flights/{flight_id}", headers=headers)
        response.raise_for_status()
        return response.json()


async def get_flight_summary_from_mcp() -> dict[str, Any]:
    """Get flight summary from MCP server via HTTP."""
    headers = await _get_auth_headers_async()
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        response = await client.get(f"{MCP_SERVER_URL}/api/summary", headers=headers)
        response.raise_for_status()
        return response.json()


async def get_all_flights_from_mcp() -> list[dict]:
    """Convenience function to get all flights (up to 200)."""
    result = await get_flights_from_mcp(limit=200, offset=0)
    return result.get("flights", [])


async def get_historical_from_mcp(
    days: int = 7,
    route: str | None = None,
    include_predictions: bool = True,
) -> dict[str, Any]:
    """Get historical payload data from MCP server via HTTP.
    
    Args:
        days: Number of historical days to retrieve (default: 7)
        route: Optional route filter (e.g., 'LAX-ORD' or 'LAX → ORD')
        include_predictions: Whether to include prediction data (default: True)
    
    Returns:
        Dict with historical data, predictions, and summary statistics
    """
    params: dict[str, Any] = {
        "days": days,
        "include_predictions": str(include_predictions).lower(),
    }
    if route:
        params["route"] = route
    
    headers = await _get_auth_headers_async()
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        response = await client.get(f"{MCP_SERVER_URL}/api/historical", params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_predictions_from_mcp(
    days: int = 7,
    route: str | None = None,
) -> dict[str, Any]:
    """Get predicted payload data from MCP server via HTTP.
    
    Args:
        days: Number of prediction days to retrieve (default: 7)
        route: Optional route filter
    
    Returns:
        Dict with prediction data
    """
    params: dict[str, Any] = {"days": days}
    if route:
        params["route"] = route
    
    headers = await _get_auth_headers_async()
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        response = await client.get(f"{MCP_SERVER_URL}/api/predictions", params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_routes_from_mcp() -> dict[str, Any]:
    """Get available routes with statistics from MCP server via HTTP."""
    headers = await _get_auth_headers_async()
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        response = await client.get(f"{MCP_SERVER_URL}/api/routes", headers=headers)
        response.raise_for_status()
        return response.json()


# ============================================================================
# Sync HTTP Client Functions (for use in sync context like agent tools)
# ============================================================================

def get_flights_sync(
    limit: int = 100,
    offset: int = 0,
    risk_level: str | None = None,
    utilization: str | None = None,
    route_from: str | None = None,
    route_to: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "utilizationPercent",
    sort_desc: bool = True,
) -> dict[str, Any]:
    """Sync version: Get flights from MCP server via HTTP."""
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "sort_desc": str(sort_desc).lower(),
    }
    if risk_level:
        params["risk_level"] = risk_level
    if utilization:
        params["utilization"] = utilization
    if route_from:
        params["route_from"] = route_from
    if route_to:
        params["route_to"] = route_to
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    
    headers = _get_auth_headers()
    with httpx.Client(timeout=MCP_TIMEOUT) as client:
        response = client.get(f"{MCP_SERVER_URL}/api/flights", params=params, headers=headers)
        response.raise_for_status()
        return response.json()


def get_all_flights_sync() -> list[dict]:
    """Sync version: Get all flights (up to 200)."""
    result = get_flights_sync(limit=200, offset=0)
    return result.get("flights", [])


def get_flight_by_id_sync(flight_id: str) -> dict[str, Any]:
    """Sync version: Get a single flight."""
    headers = _get_auth_headers()
    with httpx.Client(timeout=MCP_TIMEOUT) as client:
        response = client.get(f"{MCP_SERVER_URL}/api/flights/{flight_id}", headers=headers)
        response.raise_for_status()
        return response.json()


def get_flight_summary_sync() -> dict[str, Any]:
    """Sync version: Get flight summary."""
    headers = _get_auth_headers()
    with httpx.Client(timeout=MCP_TIMEOUT) as client:
        response = client.get(f"{MCP_SERVER_URL}/api/summary", headers=headers)
        response.raise_for_status()
        return response.json()


def get_historical_sync(
    days: int = 7,
    route: str | None = None,
    include_predictions: bool = True,
) -> dict[str, Any]:
    """Sync version: Get historical payload data from MCP server.
    
    Args:
        days: Number of historical days to retrieve (default: 7)
        route: Optional route filter (e.g., 'LAX-ORD' or 'LAX → ORD')
        include_predictions: Whether to include prediction data (default: True)
    
    Returns:
        Dict with historical data, predictions, and summary statistics
    """
    params: dict[str, Any] = {
        "days": days,
        "include_predictions": str(include_predictions).lower(),
    }
    if route:
        params["route"] = route
    
    headers = _get_auth_headers()
    with httpx.Client(timeout=MCP_TIMEOUT) as client:
        response = client.get(f"{MCP_SERVER_URL}/api/historical", params=params, headers=headers)
        response.raise_for_status()
        return response.json()


def get_predictions_sync(
    days: int = 7,
    route: str | None = None,
) -> dict[str, Any]:
    """Sync version: Get predicted payload data from MCP server.
    
    Args:
        days: Number of prediction days to retrieve (default: 7)
        route: Optional route filter
    
    Returns:
        Dict with prediction data
    """
    params: dict[str, Any] = {"days": days}
    if route:
        params["route"] = route
    
    headers = _get_auth_headers()
    with httpx.Client(timeout=MCP_TIMEOUT) as client:
        response = client.get(f"{MCP_SERVER_URL}/api/predictions", params=params, headers=headers)
        response.raise_for_status()
        return response.json()


def get_routes_sync() -> dict[str, Any]:
    """Sync version: Get available routes with statistics."""
    headers = _get_auth_headers()
    with httpx.Client(timeout=MCP_TIMEOUT) as client:
        response = client.get(f"{MCP_SERVER_URL}/api/routes", headers=headers)
        response.raise_for_status()
        return response.json()
