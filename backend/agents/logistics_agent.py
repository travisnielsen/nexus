"""
Logistics Agent with Microsoft Agent Framework

This module defines the logistics agent configuration and state schema
for the shipping logistics demo backed by v2 Responses API.

All tool implementations have been moved to the tools/ directory for better organization.
"""

from __future__ import annotations

import logging
from pathlib import Path

from agent_framework import ChatAgent, ChatClientProtocol
from agent_framework_ag_ui import AgentFrameworkAgent

# Import all tools from the tools package
from .tools import (
    # Re-export context vars for orchestrator use
    current_active_filter,
    current_selected_flight,
    # Filter tools
    filter_flights,
    reset_filters,
    # Analysis tools
    analyze_flights,
    # Recommendations tools
    get_recommendations,
    # Chart tools
    get_historical_payload,
    get_predicted_payload,
)

logger = logging.getLogger(__name__)


# State schema for the logistics agent
STATE_SCHEMA: dict[str, object] = {
    "flights": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "flightNumber": {"type": "string"},
                "flightDate": {"type": "string"},
                "from": {"type": "string"},
                "to": {"type": "string"},
                "currentPounds": {"type": "number"},
                "maxPounds": {"type": "number"},
                "currentCubicFeet": {"type": "number"},
                "maxCubicFeet": {"type": "number"},
                "utilizationPercent": {"type": "number"},
                "riskLevel": {"type": "string"},
                "sortTime": {"type": "string"},
            },
        },
        "description": "List of flight shipments to display in the dashboard.",
    },
    "selectedFlight": {
        "type": "object",
        "description": "The currently selected flight for detailed view.",
    },
    "historicalData": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "pounds": {"type": "number"},
                "cubicFeet": {"type": "number"},
                "predicted": {"type": "boolean"},
            },
        },
        "description": "Historical and predicted payload data for charts.",
    },
    "activeFilter": {
        "type": "object",
        "properties": {
            "routeFrom": {"type": "string"},
            "routeTo": {"type": "string"},
            "utilizationType": {"type": "string"},
            "riskLevel": {"type": "string"},
            "dateFrom": {"type": "string"},
            "dateTo": {"type": "string"},
            "limit": {"type": "number"},
        },
        "description": "Current filter state for the dashboard. Frontend reacts to this and fetches data via REST API.",
    },
}


def _load_system_prompt() -> str:
    """Load system prompt from markdown file."""
    prompt_path = Path(__file__).parent / "prompts" / "logistics_agent.md"
    return prompt_path.read_text().strip()


def create_logistics_agent(chat_client: ChatClientProtocol) -> AgentFrameworkAgent:
    """Instantiate the Logistics demo agent backed by Microsoft Agent Framework."""
    base_agent = ChatAgent(
        name="logistics-agent",
        instructions=_load_system_prompt(),
        chat_client=chat_client,
        tools=[
            # Dashboard filter tools - these set activeFilter in state
            # The frontend's useRenderToolCall triggers immediate REST fetch on tool start
            filter_flights,
            reset_filters,
            # Analysis tools - answer questions about data
            analyze_flights,
            # Recommendations with feedback - calls A2A agent for dynamic recommendations
            get_recommendations,
            # Chart data tools
            get_historical_payload,
            get_predicted_payload,
        ],
    )

    return AgentFrameworkAgent(
        agent=base_agent,
        name="logistics_agent",
        description="Manages shipping logistics data, flight payloads, and utilization analysis.",
        state_schema=STATE_SCHEMA,
        require_confirmation=False,
        use_service_thread=False,
    )
