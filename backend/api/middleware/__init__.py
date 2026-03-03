"""Middleware for AG-UI + Azure Foundry API integration."""

from .auth import (
    AzureADSettings,
    AzureADAuthMiddleware,
    azure_ad_settings,
    azure_scheme,
    get_azure_auth_scheme,
)

__all__ = [
    # Auth
    "AzureADSettings",
    "AzureADAuthMiddleware",
    "azure_ad_settings",
    "azure_scheme",
    "get_azure_auth_scheme",
]
