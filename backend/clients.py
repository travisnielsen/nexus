"""
Chat Client Factory

This module provides modular client creation for different Azure AI APIs.
Supports switching between Responses API and Assistants API via environment variable.
"""

from __future__ import annotations

import os
import logging
import asyncio
from typing import Literal

from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from agent_framework._clients import ChatClientProtocol
from agent_framework import azure as _azure


logger = logging.getLogger(__name__)


# Type alias for API types
ApiType = Literal["responses", "assistants"]

# Default agent name for Assistants API
DEFAULT_AGENT_NAME = "logistics-agent"

# Cache for agent ID to avoid repeated lookups
_cached_agent_id: str | None = None


def get_api_type() -> ApiType:
    """Get the configured API type from environment.
    
    Returns:
        "responses" for Responses API (default)
        "assistants" for Assistants API (thread-based)
    
    Set via AZURE_AI_API_TYPE environment variable.
    """
    api_type = os.getenv("AZURE_AI_API_TYPE", "responses").lower()
    if api_type not in ("responses", "assistants"):
        logger.warning(
            "Invalid AZURE_AI_API_TYPE '%s', defaulting to 'responses'. "
            "Valid values: 'responses', 'assistants'",
            api_type
        )
        return "responses"
    return api_type  # type: ignore


def _get_project_endpoint() -> str:
    """Get the required project endpoint from environment."""
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
    return endpoint


def _get_model_deployment_name() -> str:
    """Get the model deployment name from environment."""
    return os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")


def build_responses_client() -> ChatClientProtocol:
    """Build AzureAIClient for Foundry Agent Service Responses API.
    
    This client uses the azure.ai.projects SDK and communicates via
    response_id chaining for conversation continuity.
    
    Returns:
        ChatClientProtocol: Configured AzureAIClient instance
    """
    logger.info("Building AzureAIClient (Foundry Agent Service - Responses API)")
    
    client = _azure.AzureAIClient(
        credential=AsyncDefaultAzureCredential(),
        project_endpoint=_get_project_endpoint(),
        model_deployment_name=_get_model_deployment_name(),
    )
    
    return client


def build_agents_client() -> ChatClientProtocol:
    """Build AzureAIAgentClient for Foundry Agent Service Assistants API.
    
    This client uses the azure.ai.agents SDK and communicates via
    native thread management for conversation continuity.
    
    The client is configured with:
    - agent_name: Set to "logistics-agent" to identify the agent
    - should_cleanup_agent: Set to False to prevent deletion on shutdown
    
    Note: The AzureAIAgentClient creates a new agent on each run because
    agent_id is not provided. To reuse an existing agent, you would need
    to pass agent_id directly. However, tools and instructions are set
    per-run, so a new agent per application startup is acceptable.
    
    The agent_name ensures consistent naming in Foundry for identification.
    
    Returns:
        ChatClientProtocol: Configured AzureAIAgentClient instance
    """
    agent_name = os.getenv("AZURE_AI_AGENT_NAME", DEFAULT_AGENT_NAME)
    logger.info("Building AzureAIAgentClient (Foundry Agent Service - Assistants API)")
    logger.info("Agent name: '%s' (set AZURE_AI_AGENT_NAME to override)", agent_name)
    
    client = _azure.AzureAIAgentClient(
        credential=AsyncDefaultAzureCredential(),
        project_endpoint=_get_project_endpoint(),
        model_deployment_name=_get_model_deployment_name(),
        agent_name=agent_name,
        # Don't cleanup/delete the agent when the client closes
        # This allows the agent to persist in Foundry for inspection
        should_cleanup_agent=False,
    )
    
    return client


async def find_existing_agent_id(agent_name: str) -> str | None:
    """Look up an existing agent by name in Azure AI Foundry.
    
    Args:
        agent_name: The name of the agent to find
        
    Returns:
        The agent_id if found, None otherwise
    """
    global _cached_agent_id
    
    # Return cached ID if available
    if _cached_agent_id:
        logger.info("Using cached agent_id: %s", _cached_agent_id)
        return _cached_agent_id
    
    try:
        from azure.ai.agents.aio import AgentsClient
        
        async with AsyncDefaultAzureCredential() as credential:
            async with AgentsClient(
                endpoint=_get_project_endpoint(),
                credential=credential,
            ) as agents_client:
                # List all agents and find one with matching name
                async for agent in agents_client.list_agents():
                    if agent.name == agent_name:
                        logger.info("Found existing agent '%s' with id: %s", agent_name, agent.id)
                        _cached_agent_id = agent.id
                        return agent.id
                
                logger.info("No existing agent found with name '%s'", agent_name)
                return None
                
    except Exception as e:
        logger.warning("Failed to look up existing agent: %s", e)
        return None


def build_agents_client_with_existing_agent(agent_id: str) -> ChatClientProtocol:
    """Build AzureAIAgentClient using an existing agent ID.
    
    Args:
        agent_id: The ID of the existing agent in Foundry
        
    Returns:
        ChatClientProtocol: Configured AzureAIAgentClient instance
    """
    agent_name = os.getenv("AZURE_AI_AGENT_NAME", DEFAULT_AGENT_NAME)
    logger.info("Building AzureAIAgentClient with existing agent_id: %s", agent_id)
    
    client = _azure.AzureAIAgentClient(
        credential=AsyncDefaultAzureCredential(),
        project_endpoint=_get_project_endpoint(),
        model_deployment_name=_get_model_deployment_name(),
        agent_id=agent_id,
        agent_name=agent_name,
        should_cleanup_agent=False,
    )
    
    return client


def build_chat_client() -> tuple[ChatClientProtocol, ApiType]:
    """Factory function to build the appropriate chat client based on configuration.
    
    Reads AZURE_AI_API_TYPE environment variable to determine which client to use:
    - "responses" (default): Uses AzureAIClient (Responses API)
    - "assistants": Uses AzureAIAgentClient (Assistants API)
    
    For Assistants API, this creates a new agent on first run. To reuse an existing
    agent, call build_chat_client_async() instead.
    
    Returns:
        Tuple of (ChatClientProtocol, ApiType): The configured client and its type
    
    Raises:
        RuntimeError: If unable to initialize the chat client
    """
    try:
        api_type = get_api_type()
        
        if api_type == "assistants":
            client = build_agents_client()
        else:
            client = build_responses_client()
        
        return client, api_type

    except Exception as exc:
        raise RuntimeError(
            "Unable to initialize the chat client. "
            "Double-check your API credentials as documented in README.md."
        ) from exc


async def build_chat_client_async() -> tuple[ChatClientProtocol, ApiType]:
    """Async factory function that always creates a new agent.
    
    For Assistants API, this always creates a new agent to ensure
    instructions are up-to-date. Agent reuse was removed because
    Azure caches agent instructions, causing stale behavior.
    
    Returns:
        Tuple of (ChatClientProtocol, ApiType): The configured client and its type
    
    Raises:
        RuntimeError: If unable to initialize the chat client
    """
    try:
        api_type = get_api_type()
        
        if api_type == "assistants":
            # Always create a new agent to ensure fresh instructions
            # Agent reuse caused stale instructions to persist
            client = build_agents_client()
            logger.info("Creating new agent (reuse disabled to ensure fresh instructions)")
        else:
            client = build_responses_client()
        
        return client, api_type

    except Exception as exc:
        raise RuntimeError(
            "Unable to initialize the chat client. "
            "Double-check your API credentials as documented in README.md."
        ) from exc
