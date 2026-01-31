"""
Monkey patches for compatibility issues with Azure SDK and Agent Framework.

This module MUST be imported before any other imports in main.py to ensure
patches are applied before the affected libraries are loaded.

PATCH CONFIGURATION:
Patches can be enabled/disabled via environment variables:
- PATCH_AGUI_TEXT_MESSAGE_END=true|false (default: true)
- PATCH_CONVERSATION_ID_INJECTION=true|false (default: true)
- PATCH_TOOL_EXECUTION_SPAN=true|false (default: true)

Available patches:
1. AG-UI Event Stream fix - patches the AG-UI endpoint to handle text message
   buffering, tool call deduplication, and event stream cleanup
   (Agent Framework AG-UI compatibility with CopilotKit)

2. Conversation ID Injection - patches Responses API instrumentor to inject
   gen_ai.conversation.id from CopilotKit threadId for Azure Foundry tracing

3. Tool Execution Span - patches agent-framework's get_function_span to add
   gen_ai.conversation.id to tool execution spans
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
    
    # Patch 1: AG-UI Event Stream - needed for CopilotKit compatibility
    agui_event_stream: bool = True
    
    # Patch 2: Conversation ID Injection - needed for Azure Foundry tracing
    conversation_id_injection: bool = True
    
    # Patch 3: Tool Execution Span - adds conversation_id to tool spans
    tool_execution_span: bool = True
    
    # Track which patches were applied
    applied: list[str] = field(default_factory=list)
    
    @classmethod
    def from_environment(cls) -> "PatchConfig":
        """Load patch configuration from environment variables."""
        config = cls(
            agui_event_stream=_env_bool("PATCH_AGUI_TEXT_MESSAGE_END", True),
            conversation_id_injection=_env_bool("PATCH_CONVERSATION_ID_INJECTION", True),
            tool_execution_span=_env_bool("PATCH_TOOL_EXECUTION_SPAN", True),
        )
        
        logger.debug(
            f"Patch config: "
            f"agui_event_stream={config.agui_event_stream}, "
            f"conversation_id_injection={config.conversation_id_injection}, "
            f"tool_execution_span={config.tool_execution_span}"
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
    from .conversation_id_injection import (
        apply_conversation_id_injection_patch,
        apply_tool_execution_span_patch,
    )
    
    config = get_config()
    
    # Patch 1: AG-UI Event Stream
    if config.agui_event_stream:
        if apply_agui_event_stream_patch():
            config.applied.append("agui_event_stream")
    
    # Patch 2: Conversation ID Injection for Azure Foundry tracing
    if config.conversation_id_injection:
        if apply_conversation_id_injection_patch():
            config.applied.append("conversation_id_injection")
    
    # Patch 3: Tool Execution Span - adds conversation_id to tool spans
    if config.tool_execution_span:
        if apply_tool_execution_span_patch():
            config.applied.append("tool_execution_span")
    
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
