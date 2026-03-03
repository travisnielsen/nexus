"""
Monkey patches for compatibility issues with Azure SDK and Agent Framework.

This module MUST be imported before any other imports in main.py to ensure
patches are applied before the affected libraries are loaded.

PATCH CONFIGURATION:
Patches can be enabled/disabled via environment variables:
- PATCH_AGUI_CONTEXT_SYNC=true|false (default: false)

Available patches:
1. AG-UI Context Sync (legacy class patch) - optional global patch for
    AgentFrameworkAgent run entrypoints. Prefer instance-level wrapping via
    attach_agui_context_sync() in agents/logistics_agent.py.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# PATCH CONFIGURATION
# ============================================================================


def _env_bool(key: str, default: bool) -> bool:
    """Get a boolean from environment variable."""
    val = os.getenv(key, "").lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default


@dataclass
class PatchConfig:
    """Configuration for which patches to apply."""

    # Patch 1 (legacy): AG-UI Context Sync class monkey patch
    # Prefer instance-level wrapper in create_logistics_agent().
    agui_event_stream: bool = False

    # Track which patches were applied
    applied: list[str] = field(default_factory=list)

    @classmethod
    def from_environment(cls) -> "PatchConfig":
        """Load patch configuration from environment variables."""
        config = cls(
            agui_event_stream=_env_bool("PATCH_AGUI_CONTEXT_SYNC", True),
        )

        logger.debug(
            f"Patch config: "
            f"agui_event_stream={config.agui_event_stream}"
        )

        return config


# Global config instance
_config: PatchConfig | None = None


def get_config() -> PatchConfig:
    """Get the current patch configuration."""
    global _config
    if _config is None:
        _config = PatchConfig.from_environment()
    return _config


# ============================================================================
# PATCH APPLICATION
# ============================================================================


def apply_all_patches() -> PatchConfig:
    """Apply all configured patches and return the configuration.

    Returns:
        PatchConfig with `applied` list populated with applied patch names.
    """
    from .agui_event_stream import apply_agui_event_stream_patch
    config = get_config()

    # Patch 1 (legacy): AG-UI Context Sync class patch
    if config.agui_event_stream:
        if apply_agui_event_stream_patch():
            config.applied.append("agui_event_stream")

    if config.applied:
        logger.info(f"Applied patches: {config.applied}")
    else:
        logger.info("No patches applied")

    return config


# Apply patches on import
_applied_config = apply_all_patches()


def get_applied_patches() -> list[str]:
    """Get the list of patches that were applied."""
    return _applied_config.applied
