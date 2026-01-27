"""Middleware for AG-UI + Azure Foundry API integration."""

from .auth import (
    AzureADSettings,
    AzureADAuthMiddleware,
    azure_ad_settings,
    azure_scheme,
    get_azure_auth_scheme,
)
from .responses_api import (
    ResponsesApiThreadMiddleware,
    get_thread_response_store,
    get_current_agui_thread_id,
)
from .assistants_api import (
    AssistantsApiThreadMiddleware,
    get_assistant_thread_store,
    clear_thread_mapping,
)

__all__ = [
    # Auth
    "AzureADSettings",
    "AzureADAuthMiddleware",
    "azure_ad_settings",
    "azure_scheme",
    "get_azure_auth_scheme",
    # Responses API middleware
    "ResponsesApiThreadMiddleware",
    "get_thread_response_store",
    "get_current_agui_thread_id",
    # Assistants API middleware
    "AssistantsApiThreadMiddleware",
    "get_assistant_thread_store",
    "clear_thread_mapping",
]
