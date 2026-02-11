"""Utility modules for the logistics agent."""

# Shared data helpers and context vars
from .data_helpers import (
    current_active_filter,
    current_selected_flight,
    _get_all_flights,
    get_flight_by_id_or_number,
    _get_historical_data,
    _get_predictions,
    _get_available_routes,
)

# MCP client functions (HTTP-based)
from .mcp_client import (
    get_flights_from_mcp,
    get_flight_by_id_from_mcp,
    get_flight_summary_from_mcp,
    get_all_flights_from_mcp,
    get_historical_from_mcp,
    get_predictions_from_mcp,
    get_routes_from_mcp,
    get_flights_sync,
    get_all_flights_sync,
    get_flight_by_id_sync,
    get_flight_summary_sync,
    get_historical_sync,
    get_predictions_sync,
    get_routes_sync,
)

__all__ = [
    # Data helpers
    "current_active_filter",
    "current_selected_flight",
    "_get_all_flights",
    "get_flight_by_id_or_number",
    "_get_historical_data",
    "_get_predictions",
    "_get_available_routes",
    # MCP client functions (async)
    "get_flights_from_mcp",
    "get_flight_by_id_from_mcp",
    "get_flight_summary_from_mcp",
    "get_all_flights_from_mcp",
    "get_historical_from_mcp",
    "get_predictions_from_mcp",
    "get_routes_from_mcp",
    # MCP client functions (sync)
    "get_flights_sync",
    "get_all_flights_sync",
    "get_flight_by_id_sync",
    "get_flight_summary_sync",
    "get_historical_sync",
    "get_predictions_sync",
    "get_routes_sync",
]
