from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any, NoReturn, Protocol

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


class SessionMetadataStoreUnavailableError(RuntimeError):
    """Raised when session metadata operations fail due to Cosmos connectivity/RBAC issues."""


class SessionTranscriptAccessDeniedError(RuntimeError):
    """Raised when Foundry transcript APIs deny access for a conversation."""


class SessionMetadataRepository(Protocol):
    """Persistence boundary for session metadata.

    Concrete implementations will back this with Cosmos DB metadata.
    """

    async def list_recent_sessions(self, user_id: str, limit: int) -> list[SessionSummary]: ...

    async def get_session(self, user_id: str, session_id: str) -> SessionSummary | None: ...

    async def upsert_summary(self, user_id: str, summary: SessionSummary) -> SessionSummary: ...

    async def upsert_title(self, user_id: str, session_id: str, title: str) -> SessionSummary: ...

    async def soft_delete(self, user_id: str, session_id: str) -> bool: ...

    async def delete_metadata(self, user_id: str, session_id: str) -> bool: ...

    async def ensure_store(self) -> None: ...


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

    async def delete_metadata(self, user_id: str, session_id: str) -> bool:
        user_sessions = self._sessions.get(user_id, {})
        if session_id not in user_sessions:
            return False
        del user_sessions[session_id]
        return True

    async def ensure_store(self) -> None:
        return None


class CosmosSessionMetadataRepository:
    """Cosmos-backed repository for durable session metadata."""

    def __init__(self, *, endpoint: str, database: str, container: str) -> None:
        self._endpoint = endpoint
        self._database = database
        self._container = container
        self._bootstrap_lock = asyncio.Lock()
        self._bootstrap_state: str = "unknown"

    def _is_owner_resource_missing(self, exc: Exception) -> bool:
        sub_status = getattr(exc, "sub_status", None)
        return sub_status == 1003

    def _metadata_store_unavailable_error(
        self, *, reason: str
    ) -> SessionMetadataStoreUnavailableError:
        return SessionMetadataStoreUnavailableError(
            "Session metadata store unavailable. Ensure Terraform provisioned "
            f"Cosmos SQL database/container and RBAC correctly ({reason})."
        )

    async def _ensure_bootstrap_ready(self) -> None:
        if self._bootstrap_state == "ready":
            return
        if self._bootstrap_state == "blocked":
            raise SessionMetadataStoreUnavailableError(
                "Session metadata store unavailable. Check Cosmos DB networking and RBAC permissions."
            )

        async with self._bootstrap_lock:
            if self._bootstrap_state == "ready":
                return
            if self._bootstrap_state == "blocked":
                raise SessionMetadataStoreUnavailableError(
                    "Session metadata store unavailable. Check Cosmos DB networking and RBAC permissions."
                )

            cosmos = self._modules()
            credential = cosmos.DefaultAzureCredential()
            client = cosmos.CosmosClient(self._endpoint, credential=credential)
            try:
                try:
                    database = client.get_database_client(self._database)
                    container = database.get_container_client(self._container)
                    await container.read()
                    self._bootstrap_state = "ready"
                    logger.info(
                        "Session metadata store verified for database=%s container=%s",
                        self._database,
                        self._container,
                    )
                except cosmos.exceptions.CosmosResourceNotFoundError as exc:
                    if self._is_owner_resource_missing(exc):
                        self._bootstrap_state = "blocked"
                        logger.warning(
                            "Cosmos session metadata resources are missing (database/container not found). "
                            "Provision them via Terraform and restart the API. database=%s container=%s",
                            self._database,
                            self._container,
                        )
                        raise self._metadata_store_unavailable_error(
                            reason="resource-missing"
                        ) from exc
                    raise
                except cosmos.exceptions.CosmosHttpResponseError as exc:
                    status_code = getattr(exc, "status_code", None)
                    if status_code in {401, 403}:
                        self._bootstrap_state = "blocked"
                        logger.warning(
                            "Cosmos session metadata access denied while validating store "
                            "(status=%s). Session history will remain unavailable until RBAC/network is fixed.",
                            status_code,
                        )
                        raise self._metadata_store_unavailable_error(
                            reason=f"status-{status_code}"
                        ) from exc
                    raise
            finally:
                await client.close()
                await credential.close()

    async def _ensure_ready_or_bootstrap(self) -> None:
        await self._ensure_bootstrap_ready()

    async def list_recent_sessions(self, user_id: str, limit: int) -> list[SessionSummary]:
        await self._ensure_ready_or_bootstrap()
        query = (
            "SELECT * FROM c "
            "WHERE c.user_id = @user_id "
            "AND (NOT IS_DEFINED(c.is_deleted) OR c.is_deleted = false) "
            "ORDER BY c.last_activity_at DESC"
        )

        async with self._container_client() as container:
            results = container.query_items(
                query=query,
                parameters=[{"name": "@user_id", "value": user_id}],
                partition_key=user_id,
            )
            rows = [row async for row in results]

        summaries = [self._to_summary(row) for row in rows]
        return summaries[:limit]

    async def get_session(self, user_id: str, session_id: str) -> SessionSummary | None:
        await self._ensure_ready_or_bootstrap()
        row: dict[str, Any] | None = None
        async with self._container_client() as container:
            try:
                row = await container.read_item(item=session_id, partition_key=user_id)
            except self._exceptions().CosmosResourceNotFoundError as exc:
                if not self._is_owner_resource_missing(exc):
                    return None
                raise self._metadata_store_unavailable_error(reason="resource-missing") from exc
            if row is None:
                return None
        if bool(row.get("is_deleted")):
            return None
        return self._to_summary(row)

    async def upsert_summary(self, user_id: str, summary: SessionSummary) -> SessionSummary:
        await self._ensure_ready_or_bootstrap()
        doc = self._summary_doc(user_id=user_id, summary=summary)
        try:
            async with self._container_client() as container:
                await container.upsert_item(doc)
        except self._exceptions().CosmosResourceNotFoundError as exc:
            if self._is_owner_resource_missing(exc):
                raise self._metadata_store_unavailable_error(reason="resource-missing") from exc
            raise
        return summary

    async def upsert_title(self, user_id: str, session_id: str, title: str) -> SessionSummary:
        await self._ensure_ready_or_bootstrap()
        existing = await self.get_session(user_id=user_id, session_id=session_id)
        now = datetime.now(UTC)
        summary = SessionSummary(
            session_id=session_id,
            title=title.strip(),
            title_source=TitleSource.USER_EDITED,
            display_datetime=(existing.display_datetime if existing else now),
            last_activity_at=now,
            availability=(existing.availability if existing else SessionAvailability.AVAILABLE),
        )
        await self.upsert_summary(user_id=user_id, summary=summary)
        return summary

    async def soft_delete(self, user_id: str, session_id: str) -> bool:
        await self._ensure_ready_or_bootstrap()
        try:
            async with self._container_client() as container:
                row = await container.read_item(item=session_id, partition_key=user_id)
                row["is_deleted"] = True
                row["deleted_at"] = datetime.now(UTC).isoformat()
                await container.upsert_item(row)
                return True
        except self._exceptions().CosmosResourceNotFoundError as exc:
            if self._is_owner_resource_missing(exc):
                raise self._metadata_store_unavailable_error(reason="resource-missing") from exc
            return False

    async def delete_metadata(self, user_id: str, session_id: str) -> bool:
        await self._ensure_ready_or_bootstrap()
        try:
            async with self._container_client() as container:
                await container.delete_item(item=session_id, partition_key=user_id)
                return True
        except self._exceptions().CosmosResourceNotFoundError as exc:
            if self._is_owner_resource_missing(exc):
                raise self._metadata_store_unavailable_error(reason="resource-missing") from exc
            return False

    async def ensure_store(self) -> None:
        await self._ensure_bootstrap_ready()

    def _summary_doc(self, *, user_id: str, summary: SessionSummary) -> dict[str, Any]:
        return {
            "id": summary.session_id,
            "user_id": user_id,
            "session_id": summary.session_id,
            "title": summary.title,
            "title_source": summary.title_source.value,
            "display_datetime": summary.display_datetime.isoformat(),
            "last_activity_at": summary.last_activity_at.isoformat(),
            "availability": summary.availability.value,
            "is_deleted": False,
            "deleted_at": None,
        }

    def _to_summary(self, row: dict[str, Any]) -> SessionSummary:
        return SessionSummary(
            session_id=str(row.get("session_id") or row.get("id") or ""),
            title=str(row.get("title") or "").strip() or self._fallback_title(),
            title_source=TitleSource(
                str(row.get("title_source") or TitleSource.TIMESTAMP_FALLBACK)
            ),
            display_datetime=self._parse_datetime(row.get("display_datetime")),
            last_activity_at=self._parse_datetime(row.get("last_activity_at")),
            availability=SessionAvailability(
                str(row.get("availability") or SessionAvailability.AVAILABLE)
            ),
        )

    def _fallback_title(self) -> str:
        return f"Session {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"

    def _parse_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
        return datetime.now(UTC)

    def _modules(self):
        azure_cosmos = __import__("azure.cosmos", fromlist=["PartitionKey", "exceptions"])
        azure_cosmos_aio = __import__("azure.cosmos.aio", fromlist=["CosmosClient"])
        azure_identity_aio = __import__("azure.identity.aio", fromlist=["DefaultAzureCredential"])

        class CosmosModules:
            PartitionKey = azure_cosmos.PartitionKey
            exceptions = azure_cosmos.exceptions
            CosmosClient = azure_cosmos_aio.CosmosClient
            DefaultAzureCredential = azure_identity_aio.DefaultAzureCredential

        return CosmosModules

    def _exceptions(self):
        return self._modules().exceptions

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _container_client(self):
        cosmos = self._modules()
        credential = cosmos.DefaultAzureCredential()
        client = cosmos.CosmosClient(self._endpoint, credential=credential)
        try:
            database_client = client.get_database_client(self._database)
            container_client = database_client.get_container_client(self._container)
            yield container_client
        finally:
            await client.close()
            await credential.close()


class SessionService:
    """Application service for session list/load/mutation operations."""

    def __init__(
        self,
        repository: SessionMetadataRepository,
        chat_client: Any | None = None,
    ):
        self._repository = repository
        self._chat_client = chat_client

    def _raise_metadata_store_error(
        self,
        *,
        operation: str,
        user_id: str | None,
        session_id: str | None,
        exc: Exception,
    ) -> NoReturn:
        logger.exception(
            "Session metadata store operation failed: operation=%s user_id=%s session_id=%s",
            operation,
            user_id,
            session_id,
        )
        raise SessionMetadataStoreUnavailableError(
            "Session metadata store unavailable. Check Cosmos DB networking and RBAC permissions."
        ) from exc

    async def list_sessions(self, *, user_id: str, limit: int = 20) -> SessionListResponse:
        try:
            sessions = await self._repository.list_recent_sessions(user_id=user_id, limit=limit)
        except SessionMetadataStoreUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._raise_metadata_store_error(
                operation="list_recent_sessions",
                user_id=user_id,
                session_id=None,
                exc=exc,
            )
        visible_sessions: list[SessionSummary] = []
        for session in sessions:
            if await self.has_persisted_user_turn(session.session_id):
                visible_sessions.append(session)
                continue

            # Keep metadata store aligned with UX requirement: do not retain
            # empty (zero-turn) sessions in persisted session history.
            try:
                await self._repository.delete_metadata(
                    user_id=user_id, session_id=session.session_id
                )
            except SessionMetadataStoreUnavailableError:
                raise
            except Exception:
                logger.exception(
                    "Failed pruning zero-turn session metadata: user_id=%s session_id=%s",
                    user_id,
                    session.session_id,
                )
        return SessionListResponse(
            sessions=visible_sessions, total=len(visible_sessions), limit=limit
        )

    async def seed_session_metadata(self, *, user_id: str, session_id: str) -> SessionSummary:
        """Create initial session metadata so history can discover this session later."""

        try:
            existing = await self._repository.get_session(user_id=user_id, session_id=session_id)
        except SessionMetadataStoreUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._raise_metadata_store_error(
                operation="get_session_for_seed",
                user_id=user_id,
                session_id=session_id,
                exc=exc,
            )
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
        try:
            return await self._repository.upsert_summary(user_id=user_id, summary=summary)
        except SessionMetadataStoreUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._raise_metadata_store_error(
                operation="upsert_summary_for_seed",
                user_id=user_id,
                session_id=session_id,
                exc=exc,
            )

    async def load_session(
        self, *, user_id: str, session_id: str
    ) -> SessionLoadResponse | SessionBlockedResponse:
        try:
            transcript = await self.read_foundry_transcript_items(session_id)
        except SessionTranscriptAccessDeniedError:
            return SessionBlockedResponse(
                reason=(
                    "Session transcript is unavailable because Azure AI Foundry access was denied "
                    "(403). Verify Foundry networking/firewall access for this environment."
                ),
                code="foundry_access_denied",
            )

        restoration_manifest, restoration_status = self.build_artifact_restoration_manifest(
            session_id=session_id,
            transcript=transcript,
        )
        try:
            summary = await self._repository.get_session(user_id=user_id, session_id=session_id)
        except SessionMetadataStoreUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._raise_metadata_store_error(
                operation="get_session_for_load",
                user_id=user_id,
                session_id=session_id,
                exc=exc,
            )
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

        try:
            await self._repository.upsert_title(user_id=user_id, session_id=session_id, title=title)
        except Exception as exc:  # noqa: BLE001
            self._raise_metadata_store_error(
                operation="upsert_title",
                user_id=user_id,
                session_id=session_id,
                exc=exc,
            )
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
        try:
            await self._repository.soft_delete(user_id=user_id, session_id=session_id)
        except Exception as exc:  # noqa: BLE001
            self._raise_metadata_store_error(
                operation="soft_delete",
                user_id=user_id,
                session_id=session_id,
                exc=exc,
            )
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
        return f"Session {timestamp}"

    async def ensure_metadata_store(self) -> None:
        """Ensure metadata persistence store is ready for session operations."""
        try:
            await self._repository.ensure_store()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Session metadata store initialization failed")
            raise SessionMetadataStoreUnavailableError(
                "Session metadata store initialization failed. Check Cosmos DB networking and RBAC permissions."
            ) from exc

    async def read_foundry_transcript_items(self, session_id: str) -> list[dict[str, Any]]:
        """Read and normalize transcript items from Foundry Conversations API.

        Returns an empty transcript if Foundry chat client is not available.
        """

        openai_client = self._get_openai_client()
        if openai_client is None:
            return []

        try:
            items_response = await openai_client.conversations.items.list(session_id, order="asc")
        except Exception as exc:  # noqa: BLE001
            if self._is_foundry_access_denied(exc):
                logger.warning(
                    "Foundry transcript access denied for session_id=%s; returning blocked response",
                    session_id,
                )
                raise SessionTranscriptAccessDeniedError(
                    "Foundry transcript access denied"
                ) from exc
            raise

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

    def _is_foundry_access_denied(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code == 403:
            return True

        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if response_status == 403:
            return True

        message = str(exc).lower()
        return (
            "public access is disabled" in message
            or "permission denied" in message
            or "403" in message
        )

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

    Uses Cosmos metadata repository when endpoint is configured.
    """
    cosmos_endpoint = (
        os.getenv("SESSION_METADATA_COSMOS_DB_ENDPOINT", "").strip()
        or os.getenv("SESSION_METADATA_COSMOS_ENDPOINT", "").strip()
        or os.getenv("COSMOS_DB_ENDPOINT", "").strip()
    )
    cosmos_database = os.getenv("SESSION_METADATA_COSMOS_DATABASE", "logistics_session_metadata")
    cosmos_container = os.getenv("SESSION_METADATA_COSMOS_CONTAINER", "sessions")

    if cosmos_endpoint:
        repository: SessionMetadataRepository = CosmosSessionMetadataRepository(
            endpoint=cosmos_endpoint,
            database=cosmos_database,
            container=cosmos_container,
        )
    else:
        logger.info(
            "No Cosmos endpoint set (checked SESSION_METADATA_COSMOS_DB_ENDPOINT, "
            "SESSION_METADATA_COSMOS_ENDPOINT, COSMOS_DB_ENDPOINT); "
            "using in-memory metadata repository"
        )
        repository = InMemorySessionMetadataRepository()

    return SessionService(repository=repository, chat_client=chat_client)
