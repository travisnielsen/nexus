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


def _iter_context_items(input_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract context entries from known AG-UI request shapes.

    AG-UI/CopilotKit payloads can arrive as:
    - {"context": [...]} (current shape)
    - {"input": {"context": [...]}} (wrapped shape)
    - {"context": {...}} / {"input": {"context": {...}}} (dict form)
    """
    candidates = [
        input_data.get("context"),
        (input_data.get("input") or {}).get("context")
        if isinstance(input_data.get("input"), dict)
        else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            return [candidate]
    return []


def _parse_context_value(ctx_item: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a context entry value into a dict, if possible."""
    raw_value = ctx_item.get("value", ctx_item)

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("[AGUI-CONTEXT] Failed to parse context value: %s", e)
            return None
        return parsed if isinstance(parsed, dict) else None

    if isinstance(raw_value, dict):
        return raw_value

    logger.debug(
        "[AGUI-CONTEXT] Ignoring unsupported context value type: %s",
        type(raw_value).__name__,
    )
    return None


def _sync_active_filter(input_data: dict[str, Any]) -> None:
    """Sync activeFilter from AG-UI context payload into ContextVar."""
    from agents.utils import current_active_filter

    context_list = _iter_context_items(input_data)
    if not context_list:
        # Prevent stale filter bleed between turns when no context is sent.
        current_active_filter.set(None)
        logger.debug("[AGUI-CONTEXT] No context payload; cleared active filter")
        return

    found_active_filter = False
    latest_filter: dict[str, Any] | None = None
    saw_all_filter = False

    for ctx_item in context_list:
        if not isinstance(ctx_item, dict):
            continue

        ctx_value = _parse_context_value(ctx_item)
        if not isinstance(ctx_value, dict) or "activeFilter" not in ctx_value:
            continue

        found_active_filter = True
        filter_data = ctx_value["activeFilter"]
        if not isinstance(filter_data, dict):
            continue

        # Keep scanning to use the latest activeFilter in the payload.
        # This avoids stale state when multiple readable snapshots exist.
        if filter_data.get("filterType") == "all":
            saw_all_filter = True
            latest_filter = None
            continue

        saw_all_filter = False
        latest_filter = {
            "routeFrom": filter_data.get("routeFrom"),
            "routeTo": filter_data.get("routeTo"),
            "utilizationType": filter_data.get("utilizationType"),
            "riskLevel": filter_data.get("riskLevel"),
            "dateFrom": filter_data.get("dateFrom"),
            "dateTo": filter_data.get("dateTo"),
            "limit": filter_data.get("limit"),
        }

    if latest_filter is not None:
        current_active_filter.set(latest_filter)
        logger.debug(
            "[AGUI-CONTEXT] Synced activeFilter to ContextVar: %s",
            latest_filter,
        )
        return

    if saw_all_filter:
        current_active_filter.set(None)
        logger.debug("[AGUI-CONTEXT] Latest activeFilter.filterType=all; cleared active filter")
        return

    if not found_active_filter:
        # If context exists but doesn't include activeFilter, avoid stale state.
        current_active_filter.set(None)
        logger.debug("[AGUI-CONTEXT] Context had no activeFilter; cleared active filter")


def _extract_conversation_id(input_data: dict[str, Any]) -> str | None:
    """Extract conversation/thread id from common AG-UI payload shapes."""
    candidates: list[dict[str, Any]] = [input_data]
    wrapped = input_data.get("input")
    if isinstance(wrapped, dict):
        candidates.append(wrapped)

    keys = (
        "threadId",
        "thread_id",
        "conversationId",
        "conversation_id",
        "service_session_id",
    )

    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _sync_trace_identity(input_data: dict[str, Any]) -> None:
    """Ensure TraceIdentity exists even when custom HTTP headers are absent."""
    from agents.utils import TraceIdentity, get_trace_identity, set_trace_identity

    identity = get_trace_identity()
    if identity and identity.conversation_id:
        return

    conversation_id = _extract_conversation_id(input_data)
    if not conversation_id:
        return

    set_trace_identity(TraceIdentity(conversation_id=conversation_id))
    logger.debug("[AGUI-CONTEXT] Synced trace identity conversation_id=%s", conversation_id)


def _apply_request_context(input_data: dict[str, Any]) -> None:
    """Apply request context needed by backend tools."""
    _sync_trace_identity(input_data)
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
