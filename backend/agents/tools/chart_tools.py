"""
Chart and historical data tools.

These tools provide historical and predicted payload data for charts and trend analysis.
All data is fetched from the MCP server.
"""

from __future__ import annotations

from typing import Annotated

from agent_framework import ai_function
from pydantic import Field

from ..utils import get_historical_sync, get_predictions_sync


@ai_function(
    name="get_predicted_payload",
    description="Get predicted payload data for upcoming flights. This updates the dashboard display automatically.",
)
def get_predicted_payload(
    count: Annotated[
        int,
        Field(description="Number of prediction days to return.", default=7),
    ] = 7,
    route: Annotated[
        str | None,
        Field(description="Optional route filter (e.g., 'LAX → ORD' or 'LAX-ORD')."),
    ] = None,
) -> dict:
    """Retrieve predicted payload for upcoming flights and return structured data."""
    result = get_predictions_sync(days=count, route=route)
    predictions = result.get("predictions", [])
    
    return {
        "message": f"Predicted payload for {len(predictions)} upcoming days. The dashboard has been updated.",
        "predictions": predictions,
        "routes": result.get("routes", []),
    }


@ai_function(
    name="get_historical_payload",
    description="Get historical payload data and predictions for trend analysis. This updates the dashboard chart.",
)
def get_historical_payload(
    days: Annotated[
        int,
        Field(description="Number of historical days to retrieve.", default=7),
    ] = 7,
    include_predictions: Annotated[
        bool,
        Field(description="Whether to include prediction days.", default=True),
    ] = True,
    route: Annotated[
        str | None,
        Field(description="Optional route filter (e.g., 'LAX → ORD' or 'LAX-ORD')."),
    ] = None,
) -> dict:
    """Retrieve historical and predicted payload data and return structured data."""
    result = get_historical_sync(days=days, route=route, include_predictions=include_predictions)
    
    historical = result.get("historical", [])
    predictions = result.get("predictions", [])
    summary = result.get("summary", {})
    
    # Combine for backward compatibility with dashboard
    result_data = historical + predictions
    
    historical_count = len(historical)
    predicted_count = len(predictions)
    avg_pounds = summary.get("averagePounds", 0)
    
    return {
        "message": f"Historical payload data ({historical_count} days + {predicted_count} predictions). Average daily weight: {avg_pounds:,} lbs. The chart has been updated.",
        "historical_data": result_data,
        "summary": summary,
    }
