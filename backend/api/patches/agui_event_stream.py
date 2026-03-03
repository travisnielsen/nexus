"""
Patch: AG-UI Context Synchronization

This patch wraps AgentFrameworkAgent.run to:
1. Sync activeFilter from CopilotKit context to ContextVar for analyze_flights
2. Set OpenTelemetry conversation_id span attribute for tracing correlation

With use_service_session=True, the AG-UI framework handles thread/session
mapping natively via AgentSession. The CopilotKit threadId (a conv_* ID
created by Azure Foundry) is used directly as the service_session_id.

HISTORY:
  Previous versions mapped CopilotKit UUIDs to Azure resp_* IDs via
  ResponsesApiThreadMiddleware. That middleware has been removed in favor
  of AgentSession with pre-created Azure conversations (conv_* IDs).

STATUS: Required for project-specific context synchronization.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar

# OpenTelemetry for setting conversation_id span attribute
try:
    from opentelemetry import trace

    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    trace = None  # type: ignore

logger = logging.getLogger(__name__)

# ContextVar to track the current conversation ID (conv_* from CopilotKit threadId)
# This is used by conversation_id_injection.py to inject conversation_id into telemetry spans.
_current_conversation_id: ContextVar[str | None] = ContextVar(
    "current_conversation_id", default=None
)


def get_current_conversation_id() -> ContextVar[str | None]:
    """Get the ContextVar for the current conversation ID.

    The conversation ID is the conv_* ID from Azure Foundry, passed through
    CopilotKit as the threadId. It is set by the agui_event_stream patch
    at the start of each agent run.
    """
    return _current_conversation_id


# Tracer for creating conversation spans
_tracer = None


def _get_tracer():
    """Get or create the tracer for conversation tracking."""
    global _tracer
    if _tracer is None and HAS_OTEL:
        _tracer = trace.get_tracer("logistics-agent", "1.0.0")  # pyright: ignore[reportOptionalMemberAccess]
    return _tracer


def apply_agui_event_stream_patch() -> bool:
    """Patch AgentFrameworkAgent.run to sync context from CopilotKit.

    This patch applies project-specific context synchronization:
    - Syncs activeFilter from CopilotKit context to ContextVar for analyze_flights
    - Sets OpenTelemetry conversation_id for tracing correlation

    Thread/session management is handled natively by AgentSession with
    use_service_session=True. No middleware workarounds are needed.

    Returns:
        True if patch was applied, False otherwise.
    """
    try:
        from agent_framework_ag_ui._agent import AgentFrameworkAgent

        # Import ContextVar to set filter at request start
        from agents.utils import current_active_filter

        _original_run = AgentFrameworkAgent.run

        async def patched_run(self, input_data: dict):
            """Wrapped run that:
            1. Syncs activeFilter from CopilotKit context to ContextVar for analyze_flights
            2. Sets conversation_id ContextVar and OpenTelemetry span attribute for tracing
            """
            # ===================================================================
            # Extract thread_id (conv_* from CopilotKit) for telemetry
            # With use_service_session=True, the framework handles session
            # management — we only need the ID for OTel span attributes.
            # ===================================================================
            thread_id = (
                input_data.get("thread_id")
                or input_data.get("threadId")
                or input_data.get("forwardedProps", {}).get("threadId")
            )

            if thread_id:
                _current_conversation_id.set(thread_id)
                logger.debug(
                    "[AGUI-PATCH] Set conversation_id ContextVar: %s", thread_id
                )

            # ===================================================================
            # Sync activeFilter from CopilotKit context to ContextVar
            # ===================================================================
            context_list = input_data.get("context", [])
            if context_list:
                for ctx_item in context_list:
                    if isinstance(ctx_item, dict) and "value" in ctx_item:
                        try:
                            ctx_value = json.loads(ctx_item["value"])
                            if "activeFilter" in ctx_value:
                                filter_data = ctx_value["activeFilter"]
                                synced_filter = {
                                    "routeFrom": filter_data.get("routeFrom"),
                                    "routeTo": filter_data.get("routeTo"),
                                    "utilizationType": filter_data.get(
                                        "utilizationType"
                                    ),
                                    "riskLevel": filter_data.get("riskLevel"),
                                }
                                current_active_filter.set(synced_filter)
                                logger.debug(
                                    "[AGUI-PATCH] Synced activeFilter to ContextVar: %s",
                                    synced_filter,
                                )
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning(
                                "[AGUI-PATCH] Failed to parse context value: %s", e
                            )

            # ===================================================================
            # Set conversation_id as OpenTelemetry span attribute
            # ===================================================================
            if thread_id and HAS_OTEL:
                current_span = trace.get_current_span()  # pyright: ignore[reportOptionalMemberAccess]
                if current_span and current_span.is_recording():
                    current_span.set_attribute("gen_ai.conversation.id", thread_id)
                    current_span.set_attribute("conversation_id", thread_id)
                    logger.debug(
                        "[AGUI-PATCH] Set span attribute gen_ai.conversation.id: %s",
                        thread_id,
                    )

            # ===================================================================
            # PASS THROUGH EVENT STREAM
            # Framework handles session management and event stream natively.
            # ===================================================================
            async for event in _original_run(self, input_data):
                yield event

        # Replace the method on the class
        AgentFrameworkAgent.run = patched_run

        logger.debug(
            "Applied AG-UI context sync patch (patched AgentFrameworkAgent.run)"
        )
        return True

    except ImportError as e:
        logger.warning("Failed to apply AG-UI context sync patch: %s", e)
        return False
