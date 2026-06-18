# Contract: Feedback Query Access and Filters

## Scope
First release supports feedback retrieval for authorized backend or admin analytics consumers only.

## Access Rules
- End-user chat clients: no general query capability.
- Authorized backend/admin consumers: allowed.
- No-auth mode: feedback capture controls hidden; end-user submissions rejected.

## Query Interface (Backend/Internal)
Suggested internal endpoint contract:
- Method: `GET`
- Path: `/logistics/feedback`
- Auth: Required with admin/analytics authorization

Example query params:
- `conversation_id` (optional)
- `feedback_kind` (optional)
- `rating` (optional)
- `turn_id` (optional)
- `card_turn_id` (optional)
- `from` (optional ISO datetime)
- `to` (optional ISO datetime)
- `limit` and `cursor` (optional pagination)

## Response Shape

```json
{
  "items": [
    {
      "feedback_id": "uuid",
      "feedback_kind": "turn_response | overall_experience",
      "conversation_id": "conv_...",
      "user_id": "string",
      "rating": "positive | negative",
      "comment": "optional string",
      "turn_id": "optional string",
      "trace_id": "optional string",
      "card_turn_id": "optional string",
      "submitted_at": "2026-06-18T00:00:00Z",
      "updated_at": "2026-06-18T00:00:00Z"
    }
  ],
  "next_cursor": "optional"
}
```

## Query Guarantees
- Filter by `conversation_id`, `feedback_kind`, `rating`, `turn_id` (where applicable), and time range.
- Returned records preserve kind-specific semantics.
- Turn-response records include required turn and trace correlation fields.
- Overall records remain distinguishable while optionally retaining card-turn association.
