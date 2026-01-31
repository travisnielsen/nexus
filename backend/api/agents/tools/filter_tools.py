"""
Dashboard filter tools.

These tools control the filter state in the dashboard, allowing users
to filter flights by route, utilization, risk level, and date range.
"""

from __future__ import annotations

import logging
from typing import Annotated

from agent_framework import tool
from pydantic import Field

from ..utils import current_active_filter

logger = logging.getLogger(__name__)


@tool(
    name="filter_flights",
    description="Filter flights in the dashboard. Filters are ALWAYS additive - new filters combine with existing ones. Use reset_filters to clear all filters first.",
)
def filter_flights(
    route_from: Annotated[
        str | None,
        Field(description="Origin airport code (e.g., LAX)"),
    ] = None,
    route_to: Annotated[
        str | None,
        Field(description="Destination airport code (e.g., ORD)"),
    ] = None,
    utilization: Annotated[
        str | None,
        Field(description="Utilization filter: 'over' (>95% capacity), 'near_capacity' (85-95%), 'optimal' (50-85%), 'under' (<50%). Use 'over' for over capacity flights."),
    ] = None,
    risk_level: Annotated[
        str | None,
        Field(description="Risk level filter: critical, high, medium, low"),
    ] = None,
    date_from: Annotated[
        str | None,
        Field(description="Start date (YYYY-MM-DD)"),
    ] = None,
    date_to: Annotated[
        str | None,
        Field(description="End date (YYYY-MM-DD)"),
    ] = None,
    limit: Annotated[
        int | None,
        Field(description="Max flights to return (default 100, max 100)"),
    ] = None,
) -> dict:
    """Set the filter state. Filters are ALWAYS additive - they combine with existing filters."""
    max_limit = min(limit or 100, 100) if limit else 100
    
    # Get existing filter from ContextVar (synced from frontend context at request start)
    existing_filter = current_active_filter.get() or {}
    logger.info("[filter_flights] Existing filter from context: %s", existing_filter)
    
    # ALWAYS ADDITIVE - merge new values with existing filter
    # Only override fields that are explicitly provided
    active_filter = {
        "routeFrom": route_from.upper() if route_from else existing_filter.get("routeFrom"),
        "routeTo": route_to.upper() if route_to else existing_filter.get("routeTo"),
        "utilizationType": utilization if utilization else existing_filter.get("utilizationType"),
        "riskLevel": risk_level.lower() if risk_level else existing_filter.get("riskLevel"),
        "dateFrom": date_from if date_from else existing_filter.get("dateFrom"),
        "dateTo": date_to if date_to else existing_filter.get("dateTo"),
        "limit": max_limit,
    }
    
    logger.info("[filter_flights] Merged filter (additive): %s", active_filter)
    
    # Update the ContextVar for any subsequent tool calls in same turn
    current_active_filter.set(active_filter)
    
    # Build description for user
    filter_parts = []
    if route_from:
        filter_parts.append(f"from {route_from.upper()}")
    if route_to:
        filter_parts.append(f"to {route_to.upper()}")
    if utilization:
        filter_parts.append(utilization)
    if risk_level:
        filter_parts.append(f"{risk_level} risk")
    if date_from:
        filter_parts.append(f"from {date_from}")
    if date_to:
        filter_parts.append(f"to {date_to}")
    
    filter_desc = ', '.join(filter_parts) if filter_parts else 'all flights'
    
    return {
        "message": f"Loading flights: {filter_desc} (max {max_limit}). Dashboard is updating...",
        "activeFilter": active_filter,
    }


@tool(
    name="reset_filters",
    description="UI ACTION: Remove all active filters from the dashboard. Use ONLY when user explicitly wants to CLEAR or RESET filters, NOT for questions about flights. Trigger words: 'clear filter', 'reset filter', 'remove filter', 'show unfiltered'.",
)
def reset_filters(
    limit: Annotated[
        int | None,
        Field(description="Max flights to return (default 100, max 100)"),
    ] = None,
) -> dict:
    """Remove filters from dashboard. Frontend reacts and fetches unfiltered data via REST API."""
    max_limit = min(limit or 100, 100) if limit else 100
    
    # Clear the current_active_filter ContextVar to None (not a dict with nulls)
    # This ensures analyze_flights sees no filter is active
    current_active_filter.set(None)
    logger.info("[reset_filters] Cleared current_active_filter ContextVar to None")
    
    # Return cleared filter object for frontend state
    cleared_filter = {
        "routeFrom": None,
        "routeTo": None,
        "utilizationType": None,
        "riskLevel": None,
        "dateFrom": None,
        "dateTo": None,
        "limit": max_limit,
    }
    
    return {
        "message": f"Filters cleared. Dashboard now showing up to {max_limit} flights.",
        "activeFilter": cleared_filter,
    }
