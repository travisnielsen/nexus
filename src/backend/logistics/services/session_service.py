from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from importlib import import_module
from typing import Any, Protocol

from agents.utils.session_models import (
    ArtifactAggregateStatus,
    ArtifactRestorationStatus,
    MutationStatus,
    MutationType,
    SessionArtifact,
    SessionAvailability,
    SessionBlockedResponse,
    SessionListResponse,
    SessionLoadResponse,
    SessionMutationResult,
    SessionSummary,
    TitleSource,
    build_canonical_linkage,
)

logger = logging.getLogger(__name__)


class SessionMetadataRepository(Protocol):
    """Persistence boundary for session metadata.

    Concrete implementations will back this with Cosmos DB metadata.
    """

    async def list_recent_sessions(self, user_id: str, limit: int) -> list[SessionSummary]: ...

    async def get_session(self, user_id: str, session_id: str) -> SessionSummary | None: ...

    async def upsert_summary(self, user_id: str, summary: SessionSummary) -> SessionSummary: ...

    async def upsert_title(self, user_id: str, session_id: str, title: str) -> SessionSummary: ...

    async def soft_delete(self, user_id: str, session_id: str) -> bool: ...


class InMemorySessionMetadataRepository:
    """Temporary in-memory repo used until Cosmos metadata wiring is added."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, SessionSummary]] = {}

    async def list_recent_sessions(self, user_id: str, limit: int) -> list[SessionSummary]:
        user_sessions = list(self._sessions.get(user_id, {}).values())
        return sorted(user_sessions, key=lambda x: x.last_activity_at, reverse=True)[:limit]

    async def get_session(self, user_id: str, session_id: str) -> SessionSummary | None:
        return self._sessions.get(user_id, {}).get(session_id)

    async def upsert_summary(self, user_id: str, summary: SessionSummary) -> SessionSummary:
        user_sessions = self._sessions.setdefault(user_id, {})
        user_sessions[summary.session_id] = summary
        return summary

    async def upsert_title(self, user_id: str, session_id: str, title: str) -> SessionSummary:
        user_sessions = self._sessions.setdefault(user_id, {})
        existing = user_sessions.get(session_id)
        now = datetime.now(UTC)
        summary = SessionSummary(
            session_id=session_id,
            title=title.strip(),
            title_source=TitleSource.USER_EDITED,
            display_datetime=(existing.display_datetime if existing else now),
            last_activity_at=now,
            availability=(existing.availability if existing else SessionAvailability.AVAILABLE),
        )
        user_sessions[session_id] = summary
        return summary

    async def soft_delete(self, user_id: str, session_id: str) -> bool:
        user_sessions = self._sessions.get(user_id, {})
        if session_id not in user_sessions:
            return False
        del user_sessions[session_id]
        return True


class SessionService:
    """Application service for session list/load/mutation operations."""

    def __init__(
        self,
        repository: SessionMetadataRepository,
        chat_client: Any | None = None,
    ):
        self._repository = repository
        self._chat_client = chat_client
        self._cosmos_endpoint = os.getenv("SESSION_METADATA_COSMOS_ENDPOINT", "").strip()
        self._cosmos_database = os.getenv(
            "SESSION_METADATA_COSMOS_DATABASE", "logistics_session_metadata"
        )
        self._cosmos_container = os.getenv("SESSION_METADATA_COSMOS_CONTAINER", "sessions")

    async def list_sessions(self, *, user_id: str, limit: int = 20) -> SessionListResponse:
        sessions = await self._repository.list_recent_sessions(user_id=user_id, limit=limit)
        visible_sessions: list[SessionSummary] = []
        for session in sessions:
            if await self.has_persisted_user_turn(session.session_id):
                visible_sessions.append(session)
        return SessionListResponse(
            sessions=visible_sessions, total=len(visible_sessions), limit=limit
        )

    async def seed_session_metadata(self, *, user_id: str, session_id: str) -> SessionSummary:
        """Create initial session metadata so history can discover this session later."""

        existing = await self._repository.get_session(user_id=user_id, session_id=session_id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        summary = SessionSummary(
            session_id=session_id,
            title=self._timestamp_fallback_title(session_id=session_id),
            title_source=TitleSource.TIMESTAMP_FALLBACK,
            display_datetime=now,
            last_activity_at=now,
            availability=SessionAvailability.AVAILABLE,
        )
        return await self._repository.upsert_summary(user_id=user_id, summary=summary)

    async def load_session(
        self, *, user_id: str, session_id: str
    ) -> SessionLoadResponse | SessionBlockedResponse:
        transcript = await self.read_foundry_transcript_items(session_id)
        restoration_manifest, restoration_status = self.build_artifact_restoration_manifest(
            session_id=session_id,
            transcript=transcript,
        )
        summary = await self._repository.get_session(user_id=user_id, session_id=session_id)
        if summary is None:
            derived_title = self.derive_default_title(transcript, session_id=session_id)
            summary = SessionSummary(
                session_id=session_id,
                title=derived_title,
                title_source=(
                    TitleSource.FIRST_MESSAGE
                    if derived_title != self._timestamp_fallback_title()
                    else TitleSource.TIMESTAMP_FALLBACK
                ),
                display_datetime=datetime.now(UTC),
                last_activity_at=datetime.now(UTC),
                availability=SessionAvailability.AVAILABLE,
            )

        if summary.availability == SessionAvailability.UNAVAILABLE:
            return SessionBlockedResponse(reason="Session is unavailable and cannot be resumed")

        return SessionLoadResponse(
            session=summary,
            linkage=build_canonical_linkage(session_id),
            transcript=transcript,
            restoration_status=restoration_status,
            restoration_manifest=restoration_manifest,
        )

    def build_artifact_restoration_manifest(
        self, *, session_id: str, transcript: list[dict[str, Any]]
    ) -> tuple[list[SessionArtifact], ArtifactAggregateStatus]:
        """Build a bounded restoration manifest from normalized transcript items."""

        manifest: list[SessionArtifact] = []

        for index, item in enumerate(transcript):
            artifact = self._artifact_for_transcript_item(
                session_id=session_id,
                transcript_index=index,
                item=item,
            )
            if artifact is not None:
                manifest.append(artifact)

        if not manifest:
            return manifest, ArtifactAggregateStatus.NONE

        restored_count = sum(
            1
            for artifact in manifest
            if artifact.restoration_status == ArtifactRestorationStatus.RESTORED
        )
        if restored_count == len(manifest):
            return manifest, ArtifactAggregateStatus.FULL
        if restored_count > 0:
            return manifest, ArtifactAggregateStatus.PARTIAL
        return manifest, ArtifactAggregateStatus.NONE

    def _artifact_for_transcript_item(
        self, *, session_id: str, transcript_index: int, item: dict[str, Any]
    ) -> SessionArtifact | None:
        raw_candidate = item.get("raw")
        raw: dict[str, Any] = raw_candidate if isinstance(raw_candidate, dict) else {}
        message_id = str(item.get("id") or f"item-{transcript_index}")
        raw_type = str(raw.get("type") or "").strip().lower()

        role = str(item.get("role") or "")
        text = str(item.get("text") or "").strip()

        if role == "tool":
            if text:
                return SessionArtifact(
                    artifact_id=f"{session_id}:{message_id}:tool_result_text",
                    session_id=session_id,
                    message_id=message_id,
                    transcript_index=transcript_index,
                    artifact_type="tool_result_text",
                    restoration_status=ArtifactRestorationStatus.RESTORED,
                    restoration_descriptor={
                        "kind": "tool_result_text",
                        "text": text,
                    },
                )
            return SessionArtifact(
                artifact_id=f"{session_id}:{message_id}:tool_result_text",
                session_id=session_id,
                message_id=message_id,
                transcript_index=transcript_index,
                artifact_type="tool_result_text",
                restoration_status=ArtifactRestorationStatus.MISSING_DATA,
                fallback_text="A prior tool result could not be restored because payload text is missing.",
            )

        if raw_type in {"function_call", "function_call_output", "tool_call", "tool_result"}:
            if text:
                return SessionArtifact(
                    artifact_id=f"{session_id}:{message_id}:tool_result_text",
                    session_id=session_id,
                    message_id=message_id,
                    transcript_index=transcript_index,
                    artifact_type="tool_result_text",
                    restoration_status=ArtifactRestorationStatus.RESTORED,
                    restoration_descriptor={
                        "kind": "tool_result_text",
                        "text": text,
                    },
                )
            return SessionArtifact(
                artifact_id=f"{session_id}:{message_id}:tool_result_text",
                session_id=session_id,
                message_id=message_id,
                transcript_index=transcript_index,
                artifact_type="tool_result_text",
                restoration_status=ArtifactRestorationStatus.MISSING_DATA,
                fallback_text="A prior tool result could not be restored because payload text is missing.",
            )

        tool_calls = raw.get("tool_calls") if isinstance(raw, dict) else None
        if isinstance(tool_calls, list) and tool_calls:
            tool_names: list[str] = []
            for call in tool_calls:
                if not isinstance(call, dict):
                    continue
                function_payload = call.get("function")
                if isinstance(function_payload, dict):
                    tool_name = str(function_payload.get("name") or "").strip()
                    if tool_name:
                        tool_names.append(tool_name)
            normalized_names = [name for name in tool_names if name]
            if normalized_names:
                return SessionArtifact(
                    artifact_id=f"{session_id}:{message_id}:assistant_tool_call_summary",
                    session_id=session_id,
                    message_id=message_id,
                    transcript_index=transcript_index,
                    artifact_type="assistant_tool_call_summary",
                    restoration_status=ArtifactRestorationStatus.RESTORED,
                    restoration_descriptor={
                        "kind": "assistant_tool_call_summary",
                        "tool_names": normalized_names,
                    },
                )
            return SessionArtifact(
                artifact_id=f"{session_id}:{message_id}:assistant_tool_call_summary",
                session_id=session_id,
                message_id=message_id,
                transcript_index=transcript_index,
                artifact_type="assistant_tool_call_summary",
                restoration_status=ArtifactRestorationStatus.MISSING_DATA,
                fallback_text="A prior tool call summary could not be restored because tool metadata is missing.",
            )

        content = raw.get("content") if isinstance(raw, dict) else None
        if isinstance(content, list):
            has_non_text_content = any(
                isinstance(part, dict) and part.get("text") in (None, "") for part in content
            )
            if has_non_text_content:
                return SessionArtifact(
                    artifact_id=f"{session_id}:{message_id}:unsupported_artifact",
                    session_id=session_id,
                    message_id=message_id,
                    transcript_index=transcript_index,
                    artifact_type="unsupported_artifact",
                    restoration_status=ArtifactRestorationStatus.UNSUPPORTED,
                    fallback_text="An artifact in this message is outside the supported restoration subset.",
                )

        return None

    async def rename_session(
        self, *, user_id: str, session_id: str, title: str
    ) -> SessionMutationResult:
        normalized_title = title.strip()
        if not normalized_title:
            return SessionMutationResult(
                session_id=session_id,
                mutation_type=MutationType.RENAME,
                status=MutationStatus.REJECTED,
                conflict_reason="Title must not be empty",
            )

        await self._repository.upsert_title(user_id=user_id, session_id=session_id, title=title)
        return SessionMutationResult(
            session_id=session_id,
            mutation_type=MutationType.RENAME,
            status=MutationStatus.APPLIED,
            title=normalized_title,
        )

    async def delete_session(self, *, user_id: str, session_id: str) -> SessionMutationResult:
        # Remove from our visible-history metadata only. The underlying Foundry
        # conversation is not deleted (Foundry conversation lifecycle is managed
        # separately). Treat as idempotent: if it's already absent, that's still
        # a successful "hide from history" from the user's perspective.
        await self._repository.soft_delete(user_id=user_id, session_id=session_id)
        return SessionMutationResult(
            session_id=session_id,
            mutation_type=MutationType.DELETE,
            status=MutationStatus.APPLIED,
        )

    def derive_default_title(self, transcript: list[dict[str, Any]], *, session_id: str) -> str:
        """Derive user-facing title from first meaningful user message."""

        for item in transcript:
            if item.get("type") != "message" or item.get("role") != "user":
                continue
            text = str(item.get("text") or "").strip()
            if text:
                return text[:80]
        return self._timestamp_fallback_title(session_id=session_id)

    def _timestamp_fallback_title(self, *, session_id: str | None = None) -> str:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        suffix = f" ({session_id})" if session_id else ""
        return f"Session {timestamp}{suffix}"

    async def ensure_metadata_store(self) -> None:
        """Create metadata Cosmos database/container when endpoint is configured."""

        if not self._cosmos_endpoint:
            logger.info(
                "SESSION_METADATA_COSMOS_ENDPOINT not set; using in-memory metadata repository"
            )
            return

        azure_cosmos = import_module("azure.cosmos")
        azure_cosmos_aio = import_module("azure.cosmos.aio")
        azure_identity_aio = import_module("azure.identity.aio")

        PartitionKey = azure_cosmos.PartitionKey
        CosmosClient = azure_cosmos_aio.CosmosClient
        DefaultAzureCredential = azure_identity_aio.DefaultAzureCredential

        credential = DefaultAzureCredential()
        cosmos_client = CosmosClient(self._cosmos_endpoint, credential=credential)
        try:
            database = await cosmos_client.create_database_if_not_exists(self._cosmos_database)
            await database.create_container_if_not_exists(
                id=self._cosmos_container,
                partition_key=PartitionKey(path="/user_id"),
            )
            logger.info(
                "Session metadata bootstrap complete for database=%s container=%s",
                self._cosmos_database,
                self._cosmos_container,
            )
        finally:
            await cosmos_client.close()
            await credential.close()

    async def read_foundry_transcript_items(self, session_id: str) -> list[dict[str, Any]]:
        """Read and normalize transcript items from Foundry Conversations API.

        Returns an empty transcript if Foundry chat client is not available.
        """

        openai_client = self._get_openai_client()
        if openai_client is None:
            return []

        items_response = await openai_client.conversations.items.list(session_id, order="asc")
        items = self._coerce_items(items_response)
        normalized: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for item in items:
            entry = self._normalize_item(item)
            entry_id = entry.get("id")
            if isinstance(entry_id, str) and entry_id:
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)
            normalized.append(entry)
        return normalized

    async def has_persisted_user_turn(self, session_id: str) -> bool:
        """Return True when conversation includes at least one user message item.

        If Foundry conversations API is unavailable, fall back to visible to avoid
        blank history caused solely by temporary infrastructure unavailability.
        """

        openai_client = self._get_openai_client()
        if openai_client is None:
            return True

        try:
            items_response = await openai_client.conversations.items.list(session_id)
            items = self._coerce_items(items_response)
        except Exception:  # noqa: BLE001
            logger.exception("Failed zero-turn check for session_id=%s", session_id)
            return True

        for item in items:
            normalized = self._normalize_item(item)
            if normalized.get("type") == "message" and normalized.get("role") == "user":
                return True
        return False

    def _get_openai_client(self) -> Any | None:
        if self._chat_client is None:
            return None
        project_client = getattr(self._chat_client, "project_client", None)
        if project_client is None:
            return None
        return project_client.get_openai_client()

    def _coerce_items(self, response: Any) -> list[Any]:
        if response is None:
            return []
        if isinstance(response, list):
            return response
        data = getattr(response, "data", None)
        if isinstance(data, list):
            return data
        if isinstance(response, dict):
            maybe_data = response.get("data")
            if isinstance(maybe_data, list):
                return maybe_data
        return []

    def _normalize_item(self, item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            raw = item.model_dump(warnings=False)  # type: ignore[no-untyped-call]
        elif isinstance(item, dict):
            raw = item
        else:
            raw = {
                "id": getattr(item, "id", None),
                "type": getattr(item, "type", None),
                "role": getattr(item, "role", None),
                "content": getattr(item, "content", None),
            }

        content = raw.get("content")
        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text_value = part.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        text_parts.append(text_value)
            normalized_text = "\n".join(text_parts)
        elif isinstance(content, str):
            normalized_text = content
        else:
            normalized_text = ""

        if not normalized_text:
            output_value = raw.get("output_text") or raw.get("output") or raw.get("result")
            arguments_value = raw.get("arguments")
            function_name = raw.get("name") or raw.get("tool_name")
            raw_type = raw.get("type")

            if isinstance(output_value, str) and output_value.strip():
                normalized_text = output_value.strip()
            elif isinstance(arguments_value, str) and arguments_value.strip():
                name_prefix = (
                    f"{function_name}: " if isinstance(function_name, str) and function_name else ""
                )
                normalized_text = f"{name_prefix}{arguments_value.strip()}"
            elif isinstance(raw_type, str) and raw_type.strip():
                normalized_text = raw_type.strip()

        return {
            "id": raw.get("id"),
            "type": raw.get("type"),
            "role": raw.get("role"),
            "text": normalized_text,
            "raw": raw,
        }


def create_session_service(chat_client: Any | None = None) -> SessionService:
    """Factory for session service wiring.

    TODO: Replace in-memory repository with Cosmos-backed repository.
    """

    return SessionService(repository=InMemorySessionMetadataRepository(), chat_client=chat_client)
