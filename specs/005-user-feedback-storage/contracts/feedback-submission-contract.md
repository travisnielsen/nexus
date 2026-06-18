# Contract: Feedback Submission API

## Endpoint
- Method: `POST`
- Path: `/logistics/feedback`
- Auth: Required for end-user submission

## Request Schema

```json
{
  "feedback_kind": "turn_response | overall_experience",
  "conversation_id": "conv_...",
  "rating": "positive | negative",
  "comment": "optional string",
  "turn_id": "required for turn_response",
  "trace_id": "required for turn_response",
  "card_turn_id": "optional for overall_experience",
  "source_surface": "immediate_thumb | overall_feedback_card"
}
```

### Field Matrix

| Field | turn_response | overall_experience |
|---|---|---|
| feedback_kind | required | required |
| conversation_id | required | required |
| rating | required | required |
| comment | optional | optional |
| turn_id | required | optional |
| trace_id | required | optional |
| card_turn_id | optional | optional |
| source_surface | required (`immediate_thumb`) | required (`overall_feedback_card`) |

Validation rules:
- `conversation_id` must match `^conv_[A-Za-z0-9_-]+$`.
- Reject payloads missing required fields per kind.
- `feedback_kind` and `source_surface` pair must be compatible.

## Idempotency Contract

Deterministic logical key composition:
- Turn response:
- `turn::{user_id}::{conversation_id}::{turn_id}`
- Overall with card turn:
- `overall::{user_id}::{conversation_id}::{card_turn_id}`
- Overall without card turn:
- `overall::{user_id}::{conversation_id}::session`

Behavior:
- Upsert by idempotency key.
- Latest submission replaces prior effective record.
- Rating-first then comment submission for same logical target updates existing record.

## Response Schema

Success (storage succeeded):

```json
{
  "accepted": true,
  "feedback_id": "uuid",
  "idempotency_key": "string",
  "storage_status": "succeeded",
  "telemetry_status": "succeeded | failed",
  "message": "Feedback accepted"
}
```

Validation failure:

```json
{
  "accepted": false,
  "storage_status": "failed",
  "telemetry_status": "not_attempted",
  "error_code": "validation_error",
  "error_message": "..."
}
```

Storage failure:

```json
{
  "accepted": false,
  "storage_status": "failed",
  "telemetry_status": "not_attempted | failed",
  "error_code": "storage_error",
  "error_message": "..."
}
```

## Acceptance Boundary
- Submission is accepted only when durable storage succeeds.
- Telemetry failure does not invalidate accepted submission.
- Telemetry failure must be surfaced in response or operator-visible status.

## Client Behavior on Storage Failure
- When `accepted=false` and `storage_status=failed`, clients must display a clear, non-blocking message that feedback was not saved and allow the user to retry.
- Implement this feedback using the existing client pattern (component state + conditional inline render) and an accessible `aria-live` region; do not introduce a new toast/notification framework solely for this behavior.
