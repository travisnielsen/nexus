from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TraceIdentity(BaseModel):
    """Canonical trace identifiers propagated across service boundaries."""

    model_config = ConfigDict(extra="ignore")

    conversation_id: str = Field(min_length=1)
    turn_id: str | None = Field(default=None)
    run_id: str | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)
    a2a_interaction_id: str | None = Field(default=None)

    @field_validator(
        "conversation_id",
        "turn_id",
        "run_id",
        "tool_call_id",
        "a2a_interaction_id",
        mode="before",
    )
    @classmethod
    def _normalize_string(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            return normalized
        return value


class TraceIdentityHeaders(BaseModel):
    """HTTP header transport format for trace identity fields."""

    model_config = ConfigDict(extra="ignore")

    x_trace_conversation_id: str | None = None
    x_trace_turn_id: str | None = None
    x_trace_run_id: str | None = None
    x_trace_tool_call_id: str | None = None
    x_trace_a2a_interaction_id: str | None = None

    def to_identity(self) -> TraceIdentity | None:
        if not self.x_trace_conversation_id:
            return None
        return TraceIdentity(
            conversation_id=self.x_trace_conversation_id,
            turn_id=self.x_trace_turn_id,
            run_id=self.x_trace_run_id,
            tool_call_id=self.x_trace_tool_call_id,
            a2a_interaction_id=self.x_trace_a2a_interaction_id,
        )
