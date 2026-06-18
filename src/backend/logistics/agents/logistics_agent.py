"""
Logistics Agent with Microsoft Agent Framework

This module defines the logistics agent configuration and state schema
for the shipping logistics demo backed by Azure AI Foundry.

All tool implementations have been moved to the tools/ directory for better organization.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_framework import Agent, FunctionTool, SupportsChatGetResponse
from agent_framework.foundry import FoundryAgent, to_prompt_agent
from agent_framework_ag_ui import AgentFrameworkAgent
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
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
    show_overall_feedback_card,
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


def _sync_foundry_agent_definition_enabled() -> bool:
    """Whether to sync local prompt/tool definitions to Foundry on startup."""
    value = os.getenv("FOUNDRY_SYNC_AGENT_DEFINITION", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _build_tools() -> list[FunctionTool | Callable[..., Any]]:
    """Shared tool list for both bootstrap and runtime agents."""
    return [
        # Dashboard filter tools - these set activeFilter in state
        # The frontend's useRenderToolCall triggers immediate REST fetch on tool start
        filter_flights,
        reset_filters,
        # Analysis tools - answer questions about data
        analyze_flights,
        # Recommendations with feedback - calls A2A agent for dynamic recommendations
        get_recommendations,
        # Overall experience feedback card trigger
        show_overall_feedback_card,
        # Chart data tools
        get_historical_payload,
        get_predicted_payload,
    ]


async def ensure_foundry_agent_exists(chat_client: SupportsChatGetResponse) -> None:
    """Create or sync the Foundry prompt agent definition on startup."""
    foundry_agent_name = os.getenv("FOUNDRY_AGENT_NAME", "logistics-agent")
    project_client = chat_client.project_client  # pyright: ignore[reportAttributeAccessIssue]
    should_sync_definition = _sync_foundry_agent_definition_enabled()
    agent_exists = False

    try:
        await project_client.agents.get(agent_name=foundry_agent_name)
        agent_exists = True
    except ResourceNotFoundError:
        logger.info("Foundry agent '%s' not found; creating initial version", foundry_agent_name)
    except HttpResponseError:
        # Propagate non-404 API failures so startup fails fast with a clear platform error.
        raise

    if agent_exists and not should_sync_definition:
        logger.info(
            "Foundry agent '%s' exists; definition sync disabled, using latest version",
            foundry_agent_name,
        )
        return

    seed_agent = Agent(
        client=chat_client,
        name=foundry_agent_name,
        description="Manages shipping logistics data, flight payloads, and utilization analysis.",
        instructions=_load_system_prompt(),
        tools=_build_tools(),
    )

    created = await project_client.agents.create_version(
        agent_name=foundry_agent_name,
        definition=to_prompt_agent(seed_agent),
        description=(
            "Startup sync from local app prompt/tools."
            if agent_exists
            else "Initial logistics agent version created during startup bootstrap."
        ),
    )
    if agent_exists:
        logger.info(
            "Synced Foundry agent '%s' to new version '%s' from local definition",
            foundry_agent_name,
            getattr(created, "version", "unknown"),
        )
    else:
        logger.info(
            "Created Foundry agent '%s' initial version '%s'",
            foundry_agent_name,
            getattr(created, "version", "unknown"),
        )


def create_logistics_agent(chat_client: SupportsChatGetResponse) -> AgentFrameworkAgent:
    """Instantiate the Logistics demo agent backed by Microsoft Agent Framework."""
    foundry_agent_name = os.getenv("FOUNDRY_AGENT_NAME", "logistics-agent")

    base_agent = FoundryAgent(
        project_client=chat_client.project_client,  # pyright: ignore[reportAttributeAccessIssue]
        agent_name=foundry_agent_name,
        # Always bind by name and let Foundry resolve latest active version.
        agent_version=None,
        name="logistics-agent",
        id="logistics-agent",
        instructions=_load_system_prompt(),
        tools=_build_tools(),
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
