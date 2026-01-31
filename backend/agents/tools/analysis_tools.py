"""
Flight analysis tools.

This module provides the analyze_flights tool for answering questions
about flight data with filtering and aggregation capabilities.

AUTOMATIC FILTER CONTEXT:
- This tool automatically reads the active filter from the ContextVar
  set by filter_flights. The LLM does NOT need to pass filter parameters.
- Just call analyze_flights(question="...") and it will analyze
  whatever is currently displayed on the dashboard.
"""

from __future__ import annotations

import logging
from typing import Annotated

from agent_framework import tool
from pydantic import Field

from ..utils import _get_all_flights, current_active_filter

logger = logging.getLogger(__name__)


@tool(
    name="analyze_flights",
    description="""Answer questions about the flights currently displayed on the dashboard.

This tool analyzes the current data WITHOUT changing the dashboard display.
NEVER call filter_flights before this - just use analyze_flights directly.

Optional filter parameters let you analyze subsets:
- analyze_utilization: Count/analyze flights with specific status ("optimal", "over", "under", "near_capacity")
- analyze_route_from/to: Analyze specific route
- analyze_risk: Analyze by risk level

These filters are for ANALYSIS ONLY - they do not change the dashboard view.
""",
)
def analyze_flights(
    question: Annotated[
        str,
        Field(description="The user's question about the currently displayed flights"),
    ] = "general summary",
    analyze_utilization: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to specific utilization status ('optimal', 'over', 'under', 'near_capacity')"),
    ] = None,
    analyze_route_from: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to flights from this airport code"),
    ] = None,
    analyze_route_to: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to flights to this airport code"),
    ] = None,
    analyze_risk: Annotated[
        str | None,
        Field(description="Optional: Filter analysis to specific risk level ('critical', 'high', 'medium', 'low')"),
    ] = None,
) -> dict:
    """
    Analyze flight data with optional subset filtering.
    
    This tool can use both:
    1. The current dashboard filter (from ContextVar) 
    2. Additional analyze_* parameters for ad-hoc subset analysis
    
    The analyze_* parameters let the LLM ask questions about subsets
    (e.g., "how many optimal?") without changing the dashboard display.
    """
    # Read the current active filter from ContextVar (synced from frontend context)
    active_filter = current_active_filter.get()
    
    # Start with filter from ContextVar (what's displayed on dashboard)
    utilization_type = active_filter.get('utilizationType') if active_filter else None
    route_from = active_filter.get('routeFrom') if active_filter else None
    route_to = active_filter.get('routeTo') if active_filter else None
    risk_level = active_filter.get('riskLevel') if active_filter else None
    
    # Override with analyze_* parameters if provided (for subset analysis)
    # These let the LLM analyze subsets without changing the dashboard
    if analyze_utilization:
        utilization_type = analyze_utilization
    if analyze_route_from:
        route_from = analyze_route_from
    if analyze_route_to:
        route_to = analyze_route_to
    if analyze_risk:
        risk_level = analyze_risk
    
    # Log what we're analyzing
    logger.info(
        "[analyze_flights] Filters - context: %s, analyze_params: util=%s, route=%s->%s, risk=%s, question=%s",
        active_filter, analyze_utilization, analyze_route_from, analyze_route_to, analyze_risk, question
    )
    logger.info(
        "[analyze_flights] Effective filter: util=%s, route=%s->%s, risk=%s",
        utilization_type, route_from, route_to, risk_level
    )
    
    # Fetch ALL flights from MCP server
    all_flights = _get_all_flights()
    
    # Start with all flights
    flights = all_flights
    
    # Apply filters (from context + analyze_* overrides)
    if utilization_type == 'over':
        flights = [f for f in flights if f.get('utilizationPercent', 0) > 95]
    elif utilization_type == 'near_capacity':
        flights = [f for f in flights if 85 <= f.get('utilizationPercent', 0) <= 95]
    elif utilization_type == 'optimal':
        flights = [f for f in flights if 50 <= f.get('utilizationPercent', 0) < 85]
    elif utilization_type == 'under':
        flights = [f for f in flights if f.get('utilizationPercent', 0) < 50]
    
    # Apply route filters
    if route_from:
        flights = [f for f in flights if f.get('from', '').upper() == route_from.upper()]
    if route_to:
        flights = [f for f in flights if f.get('to', '').upper() == route_to.upper()]
    
    # Apply risk level filter
    if risk_level:
        flights = [f for f in flights if f.get('riskLevel') == risk_level.lower()]
    
    # Build filter description for logging/response
    filter_parts = []
    if route_from:
        filter_parts.append(f"from {route_from}")
    if route_to:
        filter_parts.append(f"to {route_to}")
    if utilization_type:
        filter_parts.append(f"{utilization_type} utilization")
    if risk_level:
        filter_parts.append(f"{risk_level} risk")
    
    filter_str = " with ".join(filter_parts) if filter_parts else "all flights"
    logger.info("[analyze_flights] Analyzing %d flights (%s)", len(flights), filter_str)
    
    if not flights:
        return {
            "message": f"No flights found matching the criteria ({filter_str}).",
            "flight_count": 0,
            "filter_applied": filter_str,
        }
    
    # Calculate stats
    total = len(flights)
    avg_util = sum(f.get('utilizationPercent', 0) for f in flights) / total
    
    # Risk breakdown
    critical = len([f for f in flights if f.get('riskLevel') == 'critical'])
    high = len([f for f in flights if f.get('riskLevel') == 'high'])
    medium = len([f for f in flights if f.get('riskLevel') == 'medium'])
    low = len([f for f in flights if f.get('riskLevel') == 'low'])
    
    # Route breakdown
    route_counts: dict[str, int] = {}
    for f in flights:
        route = f"{f.get('from')} → {f.get('to')}"
        route_counts[route] = route_counts.get(route, 0) + 1
    
    routes_sorted = sorted(route_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "message": f"Analyzed {total} flights" + (f" ({filter_str})" if filter_parts else ""),
        "flight_count": total,
        "filter_applied": filter_str if filter_parts else "none (all flights)",
        "average_utilization": round(avg_util, 1),
        "risk_breakdown": {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
        },
        "route_breakdown": dict(routes_sorted[:5]),
        "question": question,
    }
