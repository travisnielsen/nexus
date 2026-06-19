from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("logistics.feedback")

FeedbackKind = Literal["turn_response", "overall_experience"]
FeedbackRating = Literal["positive", "negative"]
StorageStatus = Literal["succeeded", "failed"]
TelemetryStatus = Literal["succeeded", "failed", "not_attempted"]


class FeedbackSubmission(BaseModel):
    feedback_kind: FeedbackKind
    conversation_id: str = Field(pattern=r"^conv_[A-Za-z0-9_-]+$")
    rating: FeedbackRating
    comment: str | None = None
    turn_id: str | None = None
    trace_id: str | None = None
    traceparent: str | None = None
    card_turn_id: str | None = None
    source_surface: Literal["immediate_thumb", "overall_feedback_card"]


class FeedbackOutcome(BaseModel):
    accepted: bool
    feedback_id: str | None = None
    idempotency_key: str | None = None
    updated_existing: bool | None = None
    storage_status: StorageStatus
    telemetry_status: TelemetryStatus
    error_code: str | None = None
    error_message: str | None = None
    message: str | None = None


class FeedbackRecord(BaseModel):
    id: str
    feedback_id: str
    idempotency_key: str
    feedback_kind: FeedbackKind
    conversation_id: str
    user_id: str
    rating: FeedbackRating
    comment: str | None = None
    turn_id: str | None = None
    trace_id: str | None = None
    card_turn_id: str | None = None
    source_surface: Literal["immediate_thumb", "overall_feedback_card"]
    submitted_at: str
    updated_at: str
    schema_version: str = "1.0"


class FeedbackQueryParams(BaseModel):
    conversation_id: str | None = None
    feedback_kind: str | None = None
    rating: str | None = None
    turn_id: str | None = None
    card_turn_id: str | None = None
    from_ts: datetime | None = None
    to_ts: datetime | None = None
    limit: int = 50


class FeedbackQueryResponse(BaseModel):
    items: list[dict[str, Any]]
    next_cursor: str | None = None


class FeedbackService:
    """Feedback persistence and telemetry orchestration service."""

    def __init__(self) -> None:
        self._endpoint = (
            os.getenv("FEEDBACK_COSMOS_DB_ENDPOINT")
            or os.getenv("SESSION_METADATA_COSMOS_DB_ENDPOINT")
            or os.getenv("COSMOS_DB_ENDPOINT")
        )
        self._database = os.getenv("FEEDBACK_COSMOS_DATABASE", "logistics_feedback")
        self._container = os.getenv("FEEDBACK_COSMOS_CONTAINER", "feedback_records")
        self._records: dict[str, FeedbackRecord] = {}
        self._bootstrap_lock = asyncio.Lock()
        self._bootstrap_state: str = "unknown"

    async def _ensure_bootstrap_ready(self) -> None:
        """Validate that the Cosmos DB feedback container exists and is accessible.

        Mirrors the pattern in CosmosSessionMetadataRepository: Terraform provisions
        the database and container; the API validates their existence at first use.
        Once verified the state is cached for the process lifetime.
        """

        if not self._endpoint:
            return  # Local / no-Cosmos mode; _upsert_record will raise on write.
        if self._bootstrap_state == "ready":
            return

        async with self._bootstrap_lock:
            if self._bootstrap_state == "ready":
                return

            cosmos = self._cosmos_modules()
            credential = cosmos.DefaultAzureCredential()
            client = cosmos.CosmosClient(self._endpoint, credential=credential)
            try:
                database = client.get_database_client(self._database)
                container = database.get_container_client(self._container)
                await container.read()
                self._bootstrap_state = "ready"
                logger.info(
                    "Feedback store verified for database=%s container=%s",
                    self._database,
                    self._container,
                )
            except Exception as exc:  # noqa: BLE001
                # Keep bootstrap retryable so transient firewall/network/RBAC fixes
                # can recover without requiring an API process restart.
                self._bootstrap_state = "unknown"
                logger.warning(
                    "Feedback Cosmos resources are missing or access denied. "
                    "Ensure Terraform provisioned them and networking/RBAC permits access. "
                    "database=%s container=%s error=%s",
                    self._database,
                    self._container,
                    exc,
                )
                raise RuntimeError(
                    "Feedback store unavailable. Ensure Terraform provisioned "
                    f"Cosmos SQL database/container and RBAC correctly ({exc})."
                ) from exc
            finally:
                await client.close()
                await credential.close()

    async def submit_feedback(self, payload: FeedbackSubmission, user_id: str) -> FeedbackOutcome:
        await self._ensure_bootstrap_ready()
        # Canonical session identity enforcement (T042).
        if not payload.conversation_id.startswith("conv_"):
            return FeedbackOutcome(
                accepted=False,
                storage_status="failed",
                telemetry_status="not_attempted",
                error_code="validation_error",
                error_message="conversation_id must use canonical conv_* format",
            )

        if payload.feedback_kind == "turn_response" and (
            not payload.turn_id or not payload.trace_id
        ):
            return FeedbackOutcome(
                accepted=False,
                storage_status="failed",
                telemetry_status="not_attempted",
                error_code="validation_error",
                error_message="turn_response requires turn_id and trace_id",
            )
        if (
            payload.feedback_kind == "overall_experience"
            and payload.source_surface != "overall_feedback_card"
        ):
            return FeedbackOutcome(
                accepted=False,
                storage_status="failed",
                telemetry_status="not_attempted",
                error_code="validation_error",
                error_message="overall_experience requires source_surface=overall_feedback_card",
            )
        if payload.feedback_kind == "overall_experience" and not payload.card_turn_id:
            return FeedbackOutcome(
                accepted=False,
                storage_status="failed",
                telemetry_status="not_attempted",
                error_code="validation_error",
                error_message="overall_experience requires card_turn_id",
            )

        idempotency_key = self._build_idempotency_key(payload=payload, user_id=user_id)
        existing_record = self._records.get(idempotency_key)
        now = datetime.now(UTC).isoformat()
        feedback_id = existing_record.feedback_id if existing_record else self._new_feedback_id()

        record = FeedbackRecord(
            id=idempotency_key,
            feedback_id=feedback_id,
            idempotency_key=idempotency_key,
            feedback_kind=payload.feedback_kind,
            conversation_id=payload.conversation_id,
            user_id=user_id,
            rating=payload.rating,
            comment=payload.comment,
            turn_id=payload.turn_id,
            trace_id=payload.trace_id,
            card_turn_id=payload.card_turn_id,
            source_surface=payload.source_surface,
            submitted_at=(existing_record.submitted_at if existing_record else now),
            updated_at=now,
        )

        storage_status: StorageStatus = "failed"
        telemetry_status: TelemetryStatus = "not_attempted"
        storage_error: str | None = None

        try:
            await self._upsert_record(record)
            storage_status = "succeeded"
        except Exception as exc:  # noqa: BLE001
            storage_error = str(exc)
            logger.exception("Failed to persist feedback record")

        try:
            telemetry_status = self._emit_outcome_telemetry(
                payload=payload,
                user_id=user_id,
                feedback_id=record.feedback_id,
                idempotency_key=idempotency_key,
                storage_status=storage_status,
                storage_error=storage_error,
            )
        except Exception:  # noqa: BLE001
            telemetry_status = "failed"
            logger.exception("Feedback telemetry emission failed")

        if storage_status == "failed":
            return FeedbackOutcome(
                accepted=False,
                storage_status="failed",
                telemetry_status=telemetry_status,
                error_code="storage_error",
                error_message=storage_error or "Unable to persist feedback",
            )

        return FeedbackOutcome(
            accepted=True,
            feedback_id=record.feedback_id,
            idempotency_key=idempotency_key,
            updated_existing=existing_record is not None,
            storage_status="succeeded",
            telemetry_status=telemetry_status,
            message="Feedback accepted",
        )

    async def query_feedback(self, params: FeedbackQueryParams) -> FeedbackQueryResponse:
        await self._ensure_bootstrap_ready()
        items = list(self._records.values())

        def in_range(rec: FeedbackRecord) -> bool:
            updated = datetime.fromisoformat(rec.updated_at)
            if params.from_ts and updated < params.from_ts:
                return False
            return not (params.to_ts and updated > params.to_ts)

        filtered = [
            rec
            for rec in items
            if (not params.conversation_id or rec.conversation_id == params.conversation_id)
            and (not params.feedback_kind or rec.feedback_kind == params.feedback_kind)
            and (not params.rating or rec.rating == params.rating)
            and (not params.turn_id or rec.turn_id == params.turn_id)
            and (not params.card_turn_id or rec.card_turn_id == params.card_turn_id)
            and in_range(rec)
        ]

        filtered.sort(key=lambda x: x.updated_at, reverse=True)
        return FeedbackQueryResponse(
            items=[
                {
                    "feedback_id": rec.feedback_id,
                    "feedback_kind": rec.feedback_kind,
                    "conversation_id": rec.conversation_id,
                    "user_id": rec.user_id,
                    "rating": rec.rating,
                    "comment": rec.comment,
                    "turn_id": rec.turn_id,
                    "trace_id": rec.trace_id,
                    "card_turn_id": rec.card_turn_id,
                    "submitted_at": rec.submitted_at,
                    "updated_at": rec.updated_at,
                }
                for rec in filtered[: params.limit]
            ],
            next_cursor=None,
        )

    def _build_idempotency_key(self, payload: FeedbackSubmission, user_id: str) -> str:
        if payload.feedback_kind == "turn_response":
            return f"turn::{user_id}::{payload.conversation_id}::{payload.turn_id}"
        return f"overall::{user_id}::{payload.conversation_id}::{payload.card_turn_id}"

    async def _upsert_record(self, record: FeedbackRecord) -> None:
        # Always keep an in-memory copy for query behavior and local development.
        self._records[record.id] = record

        if not self._endpoint:
            raise RuntimeError("Feedback Cosmos endpoint is not configured")

        cosmos = self._cosmos_modules()
        credential = cosmos.DefaultAzureCredential()
        client = cosmos.CosmosClient(self._endpoint, credential=credential)

        try:
            database = client.get_database_client(self._database)
            container = database.get_container_client(self._container)
            await container.upsert_item(record.model_dump())
        finally:
            await client.close()
            await credential.close()

    def _emit_outcome_telemetry(
        self,
        *,
        payload: FeedbackSubmission,
        user_id: str,
        feedback_id: str,
        idempotency_key: str,
        storage_status: StorageStatus,
        storage_error: str | None,
    ) -> TelemetryStatus:
        attrs = {
            "feedback.kind": payload.feedback_kind,
            "feedback.conversation_id": payload.conversation_id,
            "feedback.user_id": user_id,
            "feedback.feedback_id": feedback_id,
            "feedback.idempotency_key": idempotency_key,
            "feedback.storage_status": storage_status,
            "feedback.source_surface": payload.source_surface,
            "feedback.rating": payload.rating,
            "feedback.hasComment": bool(payload.comment and payload.comment.strip()),
        }
        if payload.turn_id:
            attrs["feedback.turn_id"] = payload.turn_id
        if payload.trace_id:
            attrs["feedback.trace_id"] = payload.trace_id
        if payload.traceparent:
            attrs["feedback.traceparent"] = payload.traceparent
        if payload.card_turn_id:
            attrs["feedback.card_turn_id"] = payload.card_turn_id

        include_genai_attrs = (
            os.getenv("FEEDBACK_INCLUDE_GENAI_ATTRIBUTES", "true").lower() == "true"
        )
        if include_genai_attrs:
            # Enable GenAI semantic attributes for feedback visibility in agent-focused views.
            attrs["gen_ai.operation.name"] = "user_feedback"
            attrs["gen_ai.tool.name"] = "submit_feedback"
            attrs["gen_ai.tool.type"] = "function"
            attrs["gen_ai.tool.call.id"] = feedback_id
            attrs["gen_ai.conversation.id"] = payload.conversation_id
            attrs["gen_ai.tool.status"] = storage_status
            if payload.turn_id:
                attrs["gen_ai.turn.id"] = payload.turn_id

        event_name = (
            "feedback.submission.accepted"
            if storage_status == "succeeded"
            else "feedback.storage_failure"
        )

        link_upstream_trace = os.getenv("FEEDBACK_LINK_UPSTREAM_TRACE", "false").lower() == "true"
        span_context = (
            propagate.extract({"traceparent": payload.traceparent})
            if link_upstream_trace and payload.traceparent
            else otel_context.Context()
        )
        with tracer.start_as_current_span("feedback.telemetry", context=span_context) as span:
            for key, value in attrs.items():
                span.set_attribute(key, value)
            if storage_error:
                span.set_attribute("feedback.storage_error", storage_error)
            span.add_event(event_name, attrs)

        # Structured log used by App Insights exporters and operator troubleshooting.
        logger.info(
            "feedback_outcome event=%s storage_status=%s conversation_id=%s feedback_kind=%s trace_id=%s",
            event_name,
            storage_status,
            payload.conversation_id,
            payload.feedback_kind,
            payload.trace_id,
        )

        return "succeeded"

    def _new_feedback_id(self) -> str:
        return f"fb_{int(datetime.now(UTC).timestamp() * 1000)}"

    def _cosmos_modules(self):
        azure_cosmos_aio = __import__("azure.cosmos.aio", fromlist=["CosmosClient"])
        azure_cosmos_exceptions = __import__(
            "azure.cosmos.exceptions",
            fromlist=["CosmosResourceNotFoundError", "CosmosHttpResponseError"],
        )
        azure_identity_aio = __import__("azure.identity.aio", fromlist=["DefaultAzureCredential"])

        class CosmosModules:
            CosmosClient = azure_cosmos_aio.CosmosClient
            DefaultAzureCredential = azure_identity_aio.DefaultAzureCredential
            CosmosResourceNotFoundError = azure_cosmos_exceptions.CosmosResourceNotFoundError
            CosmosHttpResponseError = azure_cosmos_exceptions.CosmosHttpResponseError

        return CosmosModules


def create_feedback_service() -> FeedbackService:
    return FeedbackService()
