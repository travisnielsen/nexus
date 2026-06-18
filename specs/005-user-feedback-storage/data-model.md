# Data Model: User Feedback Storage

## Overview
This feature models user feedback as a durable, queryable record with kind-specific fields, deterministic idempotency, and explicit submission outcome tracking.

## Entities

### 1. FeedbackRecord
- Purpose: Durable source-of-truth record for effective feedback state.
- Storage: Cosmos DB container (recommended: `feedback_records`).
- Partition key: `conversation_id`.
- Primary id: `feedback_id` (server-generated UUID).

Fields:
- `feedback_id` (string, required): Unique record identifier.
- `idempotency_key` (string, required): Deterministic key for latest-write-wins upsert behavior.
- `feedback_kind` (enum, required): `turn_response` | `overall_experience`.
- `conversation_id` (string, required): Canonical Foundry conversation id (`conv_*`).
- `user_id` (string, required): Authenticated submitter identifier.
- `rating` (enum, required): `positive` | `negative`.
- `comment` (string, optional): Free-text comment; stored as submitted.
- `submitted_at` (datetime, required): Submission timestamp (UTC).
- `updated_at` (datetime, required): Last update timestamp (UTC).
- `trace_id` (string, conditional): Required for `turn_response`; optional for `overall_experience`.
- `turn_id` (string, conditional): Required for `turn_response`; optional for `overall_experience`.
- `card_turn_id` (string, optional): Turn represented by overall-feedback card, if present.
- `source_surface` (enum, required): `immediate_thumb` | `overall_feedback_card`.
- `schema_version` (string, required): Record schema version for future compatibility.

Validation rules:
- `conversation_id` must match `^conv_[A-Za-z0-9_-]+$`.
- `feedback_kind=turn_response` requires `turn_id` and `trace_id`.
- `feedback_kind=overall_experience` forbids `turn_id` as required but allows optional `card_turn_id`.
- `rating=positive` allows optional `comment`; `rating=negative` allows optional `comment` (not required).
- Reject records with missing required kind-specific fields.

### 2. FeedbackSubmissionRequest
- Purpose: API contract for frontend-to-backend feedback submission.

Fields:
- `feedback_kind` (enum, required): `turn_response` | `overall_experience`.
- `conversation_id` (string, required)
- `rating` (enum, required): `positive` | `negative`.
- `comment` (string, optional)
- `turn_id` (string, conditional)
- `trace_id` (string, conditional)
- `card_turn_id` (string, optional)
- `source_surface` (enum, required)

Validation rules:
- Same kind-specific rules as `FeedbackRecord`.
- Reject invalid payload shape before persistence.

### 3. FeedbackSubmissionOutcome
- Purpose: Operational status model separating durability and telemetry outcomes.

Fields:
- `accepted` (bool, required)
- `storage_status` (enum, required): `succeeded` | `failed`.
- `telemetry_status` (enum, required): `succeeded` | `failed` | `not_attempted`.
- `feedback_id` (string, optional): Present when storage succeeds.
- `idempotency_key` (string, optional)
- `error_code` (string, optional)
- `error_message` (string, optional)
- `occurred_at` (datetime, required)

Validation rules:
- `accepted=true` only when `storage_status=succeeded`.
- `telemetry_status` may be `failed` while `accepted=true`.

## Deterministic Idempotency Keys

### Turn response feedback
- Composition:
- `turn::{user_id}::{conversation_id}::{turn_id}`
- Behavior:
- Upsert into same logical record; latest write replaces prior state.

### Overall experience feedback
- Composition:
- If `card_turn_id` present:
- `overall::{user_id}::{conversation_id}::{card_turn_id}`
- If `card_turn_id` absent:
- `overall::{user_id}::{conversation_id}::session`
- Behavior:
- One effective record per user and logical overall target; latest write replaces prior state.

## Relationships
- `FeedbackSubmissionRequest` -> validates into `FeedbackRecord`.
- `FeedbackRecord` -> emits `FeedbackSubmissionOutcome`.
- `FeedbackRecord` links analytics dimensions: conversation, turn/card-turn, kind, rating, time.

## State Transitions

### Submission lifecycle
1. `received` -> request received at backend boundary.
2. `validated` -> kind-specific validation passes.
3. `persisted` -> Cosmos upsert succeeds (acceptance boundary reached).
4. `telemetry_emitted` or `telemetry_failed` -> independent telemetry outcome.
5. `completed` -> outcome recorded and response returned.

### Update lifecycle (same idempotency key)
1. Existing record located via deterministic idempotency key.
2. Incoming submission replaces mutable fields (`rating`, `comment`, `updated_at`, optional correlation extensions).
3. Record version remains logically single effective record.

## Query Model
Authorized backend/admin consumers can filter by:
- `conversation_id`
- `feedback_kind`
- `rating`
- `turn_id` (where applicable)
- `card_turn_id` (where present)
- `submitted_at` range
- `user_id` (for authorized operational analysis)
