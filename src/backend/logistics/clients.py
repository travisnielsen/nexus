"""
Chat Client Factory

This module provides modular client creation for Foundry Responses API.
"""

from __future__ import annotations

import logging
import os

from agent_framework import SupportsChatGetResponse
from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

logger = logging.getLogger(__name__)


def _get_project_endpoint() -> str:
    """Get the required Foundry project endpoint from environment."""
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("FOUNDRY_PROJECT_ENDPOINT environment variable is required")
    return endpoint


def _get_model_name() -> str:
    """Get the Foundry model deployment name from environment."""
    return os.getenv("FOUNDRY_MODEL", "gpt-4o-mini")


def build_responses_client() -> SupportsChatGetResponse:
    """Build FoundryChatClient for Foundry project Responses API.

    This client targets Foundry project endpoints and supports
    app-owned instructions/tools through the standard Agent pattern.

    Returns:
        SupportsChatGetResponse: Configured FoundryChatClient instance
    """
    logger.info("Building FoundryChatClient (Foundry Responses API)")

    client = FoundryChatClient(
        credential=AsyncDefaultAzureCredential(),
        project_endpoint=_get_project_endpoint(),
        model=_get_model_name(),
    )

    return client
