from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from ..utils.telemetry_constants import (
    ATTR_A2A_INTERACTION_ID,
    ATTR_CONVERSATION_ID,
    ATTR_RUN_ID,
    ATTR_TOOL_CALL_ID,
    ATTR_TOOL_NAME,
    ATTR_TOOL_STATUS,
    ATTR_TURN_ID,
)
from ..utils.trace_context import get_trace_identity
from ..utils.trace_models import TraceIdentity

_tracer = trace.get_tracer("logistics.tools")


def validate_trace_identity_payload(payload: dict[str, Any]) -> TraceIdentity | None:
    """Validate a trace identity payload at service boundaries."""
    if not payload:
        return None
    return TraceIdentity.model_validate(payload)


def _apply_identity(span: trace.Span, identity: TraceIdentity | None) -> None:
    if not identity:
        return

    span.set_attribute(ATTR_CONVERSATION_ID, identity.conversation_id)
    if identity.turn_id:
        span.set_attribute(ATTR_TURN_ID, identity.turn_id)
    if identity.run_id:
        span.set_attribute(ATTR_RUN_ID, identity.run_id)
    if identity.tool_call_id:
        span.set_attribute(ATTR_TOOL_CALL_ID, identity.tool_call_id)
    if identity.a2a_interaction_id:
        span.set_attribute(ATTR_A2A_INTERACTION_ID, identity.a2a_interaction_id)


@contextmanager
def traced_tool_span(tool_name: str):
    """Emit a tool span with standard identity and status attributes."""
    with _tracer.start_as_current_span(f"tool.{tool_name}") as span:
        span.set_attribute(ATTR_TOOL_NAME, tool_name)
        span.set_attribute(ATTR_TOOL_STATUS, "started")
        _apply_identity(span, get_trace_identity())
        try:
            yield span
            span.set_attribute(ATTR_TOOL_STATUS, "completed")
        except Exception:
            span.set_attribute(ATTR_TOOL_STATUS, "failed")
            raise
