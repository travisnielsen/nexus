"""Tools for the logistics agent."""

# Re-export utils for backward compatibility
from ..utils import (
    current_active_filter,
    current_selected_flight,
    _get_all_flights,
    get_flight_by_id_or_number,
    _get_historical_data,
    _get_predictions,
    _get_available_routes,
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

# Filter tools
from .filter_tools import (
    filter_flights,
    reset_filters,
)

# Analysis tools
from .analysis_tools import (
    analyze_flights,
)

# Chart tools
from .chart_tools import (
    get_historical_payload,
    get_predicted_payload,
)

# Recommendations tools
from .recommendation_tools import get_recommendations

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
    # Filter tools
    "filter_flights",
    "reset_filters",
    # Analysis tools
    "analyze_flights",
    # Chart tools
    "get_historical_payload",
    "get_predicted_payload",
    # Recommendations tools
    "get_recommendations",
]
