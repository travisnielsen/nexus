"""
Chat Client Factory

This module provides modular client creation for Azure AI Responses API.
"""

from __future__ import annotations

import os
import logging

from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from agent_framework import SupportsChatGetResponse
from agent_framework import azure as _azure


logger = logging.getLogger(__name__)


def _get_project_endpoint() -> str:
    """Get the required project endpoint from environment."""
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    if not endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable is required")
    return endpoint


def _get_model_deployment_name() -> str:
    """Get the model deployment name from environment."""
    return os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")


def build_responses_client() -> SupportsChatGetResponse:
    """Build AzureAIClient for Foundry Agent Service Responses API.
    
    This client uses the azure.ai.projects SDK and communicates via
    response_id chaining for conversation continuity.
    
    Returns:
        SupportsChatGetResponse: Configured AzureAIClient instance
    """
    logger.info("Building AzureAIClient (Foundry Agent Service - Responses API)")
    
    client = _azure.AzureAIClient(
        credential=AsyncDefaultAzureCredential(),
        project_endpoint=_get_project_endpoint(),
        model_deployment_name=_get_model_deployment_name(),
    )
    
    return client
