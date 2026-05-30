"""
Logistics Agent with Microsoft Agent Framework

This module defines the logistics agent configuration and state schema
for the shipping logistics demo backed by Azure AI Foundry.

All tool implementations have been moved to the tools/ directory for better organization.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from agent_framework import SupportsChatGetResponse
from agent_framework.foundry import FoundryAgent
from agent_framework_ag_ui import AgentFrameworkAgent
from opentelemetry import trace

from patches.agui_event_stream import attach_agui_context_sync

# Import all tools from the tools package
from .tools import (
    # Analysis tools
    analyze_flights,
    # Re-export context vars for orchestrator use
    filter_flights,
    # Chart tools
    get_historical_payload,
    get_predicted_payload,
    # Recommendations tools
    get_recommendations,
    reset_filters,
)
from .utils import get_trace_identity

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("logistics.agent")


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


def create_logistics_agent(chat_client: SupportsChatGetResponse) -> AgentFrameworkAgent:
    """Instantiate the Logistics demo agent backed by Microsoft Agent Framework."""
    foundry_agent_name = os.getenv("FOUNDRY_AGENT_NAME", "logistics-agent")
    foundry_agent_version = os.getenv("FOUNDRY_AGENT_VERSION") or None

    base_agent = FoundryAgent(
        project_client=chat_client.project_client,  # pyright: ignore[reportAttributeAccessIssue]
        agent_name=foundry_agent_name,
        agent_version=foundry_agent_version,
        name="logistics-agent",
        id="logistics-agent",
        instructions=_load_system_prompt(),
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

    agui_agent = AgentFrameworkAgent(
        agent=base_agent,
        name="logistics_agent",
        description="Manages shipping logistics data, flight payloads, and utilization analysis.",
        state_schema=STATE_SCHEMA,
        require_confirmation=False,
        use_service_session=True,
    )

    # Safer than global monkey patching: attach context sync to this instance only.
    attach_agui_context_sync(agui_agent)

    original_run = agui_agent.run

    async def traced_run(input_data: dict[str, object]):
        with tracer.start_as_current_span("agent.run") as span:
            span.set_attribute("gen_ai.agent.name", "logistics-agent")
            identity = get_trace_identity()
            if identity:
                span.set_attribute("gen_ai.conversation.id", identity.conversation_id)
                if identity.run_id:
                    span.set_attribute("gen_ai.run.id", identity.run_id)
                if identity.turn_id:
                    span.set_attribute("gen_ai.turn.id", identity.turn_id)
            async for event in original_run(input_data):
                yield event

    agui_agent.run = traced_run

    return agui_agent
