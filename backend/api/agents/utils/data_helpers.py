"""
Shared data access helpers for logistics tools.

This module provides common data loading and access functions
used across multiple tool modules.

All data is loaded from MCP server via HTTP.
Configure via environment variables:
- MCP_SERVER_URL: Base URL of the MCP server (default: http://localhost:8001)
- MCP_TIMEOUT: Request timeout in seconds (default: 10.0)
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

logger = logging.getLogger(__name__)

# ContextVar to pass current filter from request to tools
# This allows tools to automatically use the current dashboard filter
current_active_filter: ContextVar[dict[str, Any] | None] = ContextVar("current_active_filter", default=None)

# ContextVar to pass selected flight from request to tools
# This allows tools to automatically analyze the selected flight when user asks about "this flight"
current_selected_flight: ContextVar[dict[str, Any] | None] = ContextVar("current_selected_flight", default=None)


def _get_all_flights() -> list[dict[str, Any]]:
    """
    Get all flights from MCP server.
    
    This is a sync function that uses the sync MCP client.
    For async contexts, use get_all_flights_from_mcp() from mcp_client.
    """
    from .mcp_client import get_all_flights_sync
    return get_all_flights_sync()


def _get_historical_data(
    days: int = 50,
    route: str | None = None,
    include_predictions: bool = True,
) -> list[dict[str, Any]]:
    """
    Get historical and prediction data from MCP server.
    
    Args:
        days: Number of historical days to retrieve (default: 50 to get all)
        route: Optional route filter
        include_predictions: Whether to include predictions
    
    Returns:
        List of historical data records (combines historical and predictions)
    """
    from .mcp_client import get_historical_sync
    
    try:
        result = get_historical_sync(days=days, route=route, include_predictions=include_predictions)
        # Combine historical and predictions into a single list for backward compatibility
        historical = result.get("historical", [])
        predictions = result.get("predictions", []) if include_predictions else []
        return historical + predictions
    except Exception as e:
        logger.warning(f"Failed to get historical data from MCP: {e}")
        return []


def _get_predictions(days: int = 7, route: str | None = None) -> list[dict]:
    """
    Get prediction data from MCP server.
    
    Args:
        days: Number of prediction days to retrieve
        route: Optional route filter
    
    Returns:
        List of prediction records
    """
    from .mcp_client import get_predictions_sync
    
    try:
        result = get_predictions_sync(days=days, route=route)
        return result.get("predictions", [])
    except Exception as e:
        logger.warning(f"Failed to get predictions from MCP: {e}")
        return []


def _get_available_routes() -> list[dict]:
    """
    Get available routes with statistics from MCP server.
    
    Returns:
        List of route records with statistics
    """
    from .mcp_client import get_routes_sync
    
    try:
        result = get_routes_sync()
        return result.get("routes", [])
    except Exception as e:
        logger.warning(f"Failed to get routes from MCP: {e}")
        return []


def get_flight_by_id_or_number(identifier: str) -> dict[str, Any] | None:
    """
    Helper to find a flight by ID or flight number from MCP server.
    """
    from .mcp_client import get_flight_by_id_sync
    result = get_flight_by_id_sync(identifier)
    return result.get("flight")
