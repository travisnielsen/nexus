"""
Recommendations tools.

This module provides tools for generating risk mitigation and optimization
recommendations by calling an external A2A recommendations agent.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Annotated

from agent_framework import ai_function
from agent_framework_a2a import A2AAgent
from pydantic import Field

from ..utils import _get_flight_by_id_or_number, current_selected_flight

logger = logging.getLogger(__name__)

# Default URL for the recommendations agent (can be overridden via environment variable)
# Note: A2A agents expose their card at /.well-known/agent.json
RECOMMENDATIONS_AGENT_URL = "http://localhost:5002"


def _get_recommendations_agent_url() -> str:
    """Get the recommendations agent URL from environment or use default."""
    return os.getenv("RECOMMENDATIONS_AGENT_URL", RECOMMENDATIONS_AGENT_URL)


# Cached A2A agent instance
_a2a_agent: A2AAgent | None = None


def _get_a2a_agent() -> A2AAgent:
    """Get or create the A2A agent client."""
    global _a2a_agent
    if _a2a_agent is None:
        agent_url = _get_recommendations_agent_url()
        logger.info(f"Creating A2AAgent for {agent_url}")
        _a2a_agent = A2AAgent(
            name="recommendations-client",
            url=agent_url,
            timeout=60.0,
        )
    return _a2a_agent


async def call_recommendations_agent(query: str) -> str:
    """
    Call the external recommendations agent using A2A protocol.
    
    Args:
        query: The query to send to the recommendations agent.
        
    Returns:
        The response text from the recommendations agent.
    """
    agent_url = _get_recommendations_agent_url()
    logger.info(f"Calling A2A recommendations agent at {agent_url} with query: {query}")
    
    try:
        agent = _get_a2a_agent()
        
        # Run the agent with the query
        response = await agent.run(query)
        
        # The AgentResponse has a __str__ that returns the text content
        response_text = str(response)
        
        if response_text:
            logger.info(f"Received A2A response: {response_text[:100]}...")
            return response_text
        
        # Fallback: try to extract from messages
        if hasattr(response, 'messages') and response.messages:
            texts = []
            for msg in response.messages:
                if hasattr(msg, 'contents') and msg.contents:
                    for content in msg.contents:
                        if hasattr(content, 'text'):
                            texts.append(content.text)
            if texts:
                return "\n".join(texts)
        
        logger.warning("No text content found in A2A response")
        return "No recommendations available."
                
    except Exception as e:
        logger.error(f"Error calling A2A recommendations agent: {e}")
        raise


@ai_function(
    name="get_recommendations",
    description="Display risk mitigation recommendations for a high-risk or critical flight. Shows interactive recommendations in the chat with feedback options. Use when user asks about recommendations, mitigation strategies, or what to do about a risky flight. Can also show optimization suggestions for under-utilized (low risk) flights.",
)
async def get_recommendations(
    flight_id: Annotated[
        str | None,
        Field(description="ID or flight number of the flight to show recommendations for. If not provided, uses the currently selected flight from the UI."),
    ] = None,
) -> dict:
    """Generate and return recommendations for a flight by calling external A2A agent. Rendered as interactive card in chat."""
    
    # Determine which flight to analyze
    flight = None
    
    # Priority 1: Explicit flight_id parameter
    if flight_id:
        flight = _get_flight_by_id_or_number(flight_id)
    
    # Priority 2: Currently selected flight from UI
    if not flight:
        selected = current_selected_flight.get()
        if selected:
            flight = selected
    
    if not flight:
        return {
            "error": "No flight specified or selected. Please select a flight or provide a flight number.",
            "recommendations": [],
        }
    
    flight_number = flight.get("flightNumber", "unknown")
    risk_level = flight.get("riskLevel", "medium")
    utilization = flight.get("utilizationPercent", 0)
    route_from = flight.get("from", "?")
    route_to = flight.get("to", "?")
    route = f"{route_from} → {route_to}"
    
    # For medium risk, no recommendations needed
    if risk_level == "medium":
        return {
            "flightId": flight.get("id", ""),
            "flightNumber": flight_number,
            "route": route,
            "riskLevel": risk_level,
            "utilizationPercent": utilization,
            "recommendations": [],
            "message": f"Flight {flight_number} is at optimal utilization ({utilization:.1f}%). No action needed.",
            "generatedAt": datetime.utcnow().isoformat() + "Z",
        }
    
    # Build context for the A2A recommendations agent
    if risk_level in ("high", "critical"):
        context = (
            f"Flight {flight_number} from {route_from} to {route_to} is at {utilization:.1f}% capacity "
            f"with {risk_level} risk level. Provide 3-4 specific risk mitigation recommendations "
            f"to prevent delays and optimize cargo distribution."
        )
    else:  # low risk
        context = (
            f"Flight {flight_number} from {route_from} to {route_to} is under-utilized at {utilization:.1f}% capacity "
            f"with low risk. Provide 3 optimization recommendations to better utilize this capacity."
        )
    
    # Call the A2A recommendations agent
    recommendations = []
    try:
        logger.info("[get_recommendations] Calling A2A agent for flight %s", flight_number)
        response = await call_recommendations_agent(context)
        
        # Parse the response into individual recommendations
        # The agent returns text with numbered recommendations
        lines = response.strip().split("\n")
        rec_id = 0
        for line in lines:
            line = line.strip()
            # Skip empty lines and headers
            if not line or line.lower().startswith("here are") or line.lower().startswith("recommendations"):
                continue
            # Remove leading numbers like "1.", "2.", etc.
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
            if cleaned and len(cleaned) > 10:  # Minimum length for a valid recommendation
                rec_id += 1
                category = "mitigation" if risk_level in ("high", "critical") else "optimization"
                recommendations.append({
                    "id": f"rec-a2a-{rec_id}",
                    "text": cleaned,
                    "category": category,
                })
                # Limit to 5 recommendations max
                if len(recommendations) >= 5:
                    break
        
        # Ensure at least 2 recommendations (pad with generic if needed)
        if len(recommendations) < 2:
            if risk_level in ("high", "critical"):
                recommendations.append({
                    "id": "rec-generic-1",
                    "text": "Review cargo priorities and consider redistributing to alternative flights",
                    "category": "mitigation",
                })
            else:
                recommendations.append({
                    "id": "rec-generic-1",
                    "text": "Consider accepting additional cargo to optimize capacity utilization",
                    "category": "optimization",
                })
        
        logger.info("[get_recommendations] Received %d recommendations from A2A agent for flight %s",
                    len(recommendations), flight_number)
                    
    except Exception as e:
        logger.error("[get_recommendations] Error calling A2A agent: %s", e)
        # Fall back to a generic recommendation on error
        recommendations = [{
            "id": "rec-fallback",
            "text": f"Unable to fetch recommendations from external agent. Please review flight {flight_number} manually.",
            "category": "error",
        }]
    
    # Add urgency note for high utilization
    if utilization > 95 and risk_level in ("high", "critical"):
        recommendations.insert(0, {
            "id": "rec-urgent",
            "text": f"URGENT: Flight is at {utilization:.1f}% capacity. Immediate action required to prevent delays",
            "category": "urgent",
        })
    
    return {
        "flightId": flight.get("id", ""),
        "flightNumber": flight_number,
        "route": route,
        "riskLevel": risk_level,
        "utilizationPercent": utilization,
        "recommendations": recommendations,
        "generatedAt": datetime.utcnow().isoformat() + "Z",
    }
