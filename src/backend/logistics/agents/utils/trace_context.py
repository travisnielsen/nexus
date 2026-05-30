from __future__ import annotations

from contextvars import ContextVar

from .trace_models import TraceIdentity

_current_trace_identity: ContextVar[TraceIdentity | None] = ContextVar(
    "current_trace_identity",
    default=None,
)


def set_trace_identity(identity: TraceIdentity | None) -> None:
    _current_trace_identity.set(identity)


def get_trace_identity() -> TraceIdentity | None:
    return _current_trace_identity.get()


def clear_trace_identity() -> None:
    _current_trace_identity.set(None)
