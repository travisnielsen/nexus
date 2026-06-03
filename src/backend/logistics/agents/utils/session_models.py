from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TitleSource(StrEnum):
    FIRST_MESSAGE = "first_message"
    TIMESTAMP_FALLBACK = "timestamp_fallback"
    USER_EDITED = "user_edited"


class SessionAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ArtifactAggregateStatus(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class ArtifactRestorationStatus(StrEnum):
    RESTORED = "restored"
    UNSUPPORTED = "unsupported"
    MISSING_DATA = "missing_data"
    FAILED = "failed"


class SupportedArtifactType(StrEnum):
    TOOL_RESULT_TEXT = "tool_result_text"
    ASSISTANT_TOOL_CALL_SUMMARY = "assistant_tool_call_summary"


class MutationType(StrEnum):
    RENAME = "rename"
    DELETE = "delete"


class MutationStatus(StrEnum):
    APPLIED = "applied"
    REJECTED = "rejected"


class CanonicalSessionLinkage(BaseModel):
    """Identity continuity contract across frontend/backend/foundry layers."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    copilot_thread_id: str = Field(min_length=1)
    maf_service_session_id: str = Field(min_length=1)
    foundry_conversation_id: str = Field(min_length=1)
    last_verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def ensure_identity_continuity(self) -> CanonicalSessionLinkage:
        ids = {
            self.session_id,
            self.copilot_thread_id,
            self.maf_service_session_id,
            self.foundry_conversation_id,
        }
        if len(ids) != 1:
            raise ValueError("Canonical linkage IDs must match exactly")
        if not self.session_id.startswith("conv_"):
            raise ValueError("Session ID must use conv_* format")
        return self


class SessionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    title_source: TitleSource
    display_datetime: datetime
    last_activity_at: datetime
    availability: SessionAvailability


class SessionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: list[SessionSummary]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=20)


class SessionLoadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: SessionSummary
    linkage: CanonicalSessionLinkage
    transcript: list[dict[str, Any]]
    restoration_status: ArtifactAggregateStatus = Field(default=ArtifactAggregateStatus.NONE)
    restoration_manifest: list[SessionArtifact] = Field(default_factory=list)


class SessionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    transcript_index: int = Field(ge=0)
    artifact_type: str = Field(min_length=1)
    restoration_status: ArtifactRestorationStatus
    restoration_descriptor: dict[str, Any] | None = None
    fallback_text: str | None = None


class SessionBlockedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocked: bool = True
    reason: str
    code: str = "session_unavailable"


class SessionErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    code: str


class SessionRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=160)


class SessionMutationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    mutation_type: MutationType
    status: MutationStatus
    title: str | None = None
    conflict_reason: str | None = None


def build_canonical_linkage(session_id: str) -> CanonicalSessionLinkage:
    """Build a canonical ID mapping where all IDs must remain equal."""

    return CanonicalSessionLinkage(
        session_id=session_id,
        copilot_thread_id=session_id,
        maf_service_session_id=session_id,
        foundry_conversation_id=session_id,
    )
