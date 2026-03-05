"""AG-UI context synchronization helpers.

This module provides a safe bridge between frontend CopilotKit readable context
and backend tool execution context.

Key responsibility:
1. Sync activeFilter from AG-UI request context into current_active_filter

Prefer instance-level wrapping via attach_agui_context_sync() instead of a
global class monkey patch.
"""

from __future__ import annotations

import json
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


def _sync_active_filter(input_data: dict[str, Any]) -> None:
    """Sync activeFilter from AG-UI context payload into ContextVar."""
    from agents.utils import current_active_filter

    context_list = input_data.get("context", [])
    if not context_list:
        # Prevent stale filter bleed between turns when no context is sent.
        current_active_filter.set(None)
        logger.debug("[AGUI-CONTEXT] No context payload; cleared active filter")
        return

    found_active_filter = False

    for ctx_item in context_list:
        if not isinstance(ctx_item, dict) or "value" not in ctx_item:
            continue

        try:
            raw_value = ctx_item["value"]
            if isinstance(raw_value, str):
                ctx_value = json.loads(raw_value)
            elif isinstance(raw_value, dict):
                ctx_value = raw_value
            else:
                logger.debug(
                    "[AGUI-CONTEXT] Ignoring unsupported context value type: %s",
                    type(raw_value).__name__,
                )
                continue

            if "activeFilter" in ctx_value:
                found_active_filter = True
                filter_data = ctx_value["activeFilter"]

                # When UI indicates "all", treat as no active filter.
                if isinstance(filter_data, dict) and filter_data.get("filterType") == "all":
                    current_active_filter.set(None)
                    logger.debug(
                        "[AGUI-CONTEXT] activeFilter.filterType=all; cleared active filter"
                    )
                    return

                synced_filter = {
                    "routeFrom": filter_data.get("routeFrom"),
                    "routeTo": filter_data.get("routeTo"),
                    "utilizationType": filter_data.get("utilizationType"),
                    "riskLevel": filter_data.get("riskLevel"),
                    "dateFrom": filter_data.get("dateFrom"),
                    "dateTo": filter_data.get("dateTo"),
                    "limit": filter_data.get("limit"),
                }
                current_active_filter.set(synced_filter)
                logger.debug(
                    "[AGUI-CONTEXT] Synced activeFilter to ContextVar: %s",
                    synced_filter,
                )
                return
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("[AGUI-CONTEXT] Failed to parse context value: %s", e)

    if not found_active_filter:
        # If context exists but doesn't include activeFilter, avoid stale state.
        current_active_filter.set(None)
        logger.debug("[AGUI-CONTEXT] Context had no activeFilter; cleared active filter")


def _apply_request_context(input_data: dict[str, Any]) -> None:
    """Apply request context needed by backend tools."""
    _sync_active_filter(input_data)


def attach_agui_context_sync(agent_runner: object) -> bool:
    """Attach context sync to a specific AG-UI protocol runner instance.

    This is safer than globally monkey-patching the framework class. It wraps
    the runner instance's AG-UI entry method (`run` or `run_agent`) and applies
    context synchronization before delegating to the original implementation.

    Args:
        agent_runner: AgentFrameworkAgent instance (or compatible object)

    Returns:
        True if wrapper attached, False otherwise.
    """
    run_method_name = None
    if callable(getattr(agent_runner, "run", None)):
        run_method_name = "run"
    elif callable(getattr(agent_runner, "run_agent", None)):
        run_method_name = "run_agent"

    if run_method_name is None:
        logger.warning("[AGUI-CONTEXT] Could not attach context sync: no run/run_agent method")
        return False

    original_run = getattr(agent_runner, run_method_name)
    if getattr(original_run, "_agui_context_sync_wrapped", False):
        return True

    async def wrapped_run(input_data: dict[str, Any]):
        _apply_request_context(input_data)
        async for event in original_run(input_data):
            yield event

    cast(Any, wrapped_run)._agui_context_sync_wrapped = True
    setattr(agent_runner, run_method_name, wrapped_run)
    logger.debug(
        "[AGUI-CONTEXT] Attached instance context sync wrapper to %s",
        run_method_name,
    )
    return True


def apply_agui_event_stream_patch() -> bool:
    """Backward-compatible global class patch.

    Prefer attach_agui_context_sync() for instance-level wrapping.

    Returns:
        True if patch was applied, False otherwise.
    """
    try:
        from agent_framework_ag_ui._agent import AgentFrameworkAgent

        if callable(getattr(AgentFrameworkAgent, "run", None)):
            method_name = "run"
        elif callable(getattr(AgentFrameworkAgent, "run_agent", None)):
            method_name = "run_agent"
        else:
            logger.warning(
                "Failed to apply AG-UI context sync patch: no run/run_agent on AgentFrameworkAgent"
            )
            return False

        original_run = getattr(AgentFrameworkAgent, method_name)
        if getattr(original_run, "_agui_context_sync_wrapped", False):
            return True

        async def patched_run(self, input_data: dict[str, Any]):
            _apply_request_context(input_data)
            async for event in original_run(self, input_data):
                yield event

        cast(Any, patched_run)._agui_context_sync_wrapped = True
        setattr(AgentFrameworkAgent, method_name, patched_run)

        logger.debug(
            "Applied AG-UI context sync class patch (patched AgentFrameworkAgent.%s)",
            method_name,
        )
        return True

    except Exception as e:
        logger.warning("Failed to apply AG-UI context sync patch: %s", e)
        return False
