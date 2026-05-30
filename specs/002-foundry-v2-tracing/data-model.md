# Data Model: Full Foundry V2 Tracing

## Entity: TraceConversation

- Description: Root trace container for a single conversation.
- Fields:
  - `conversation_id` (string): Stable conversation identity used across frontend/backend.
  - `thread_id` (string): AG-UI thread identifier used by CopilotKit runtime.
  - `started_at` (datetime)
  - `ended_at` (datetime | null)
  - `status` (enum): `active` | `completed` | `failed`.
- Relationships:
  - One `TraceConversation` has many `TraceTurn`.

## Entity: TraceTurn

- Description: One user/assistant interaction turn within a conversation.
- Fields:
  - `turn_id` (string): Stable per-turn identifier.
  - `conversation_id` (string, FK -> TraceConversation)
  - `run_id` (string): AG-UI run identity.
  - `started_at` (datetime)
  - `ended_at` (datetime | null)
  - `status` (enum): `started` | `completed` | `failed`.
  - `error_code` (string | null)
  - `error_message` (string | null)
- Relationships:
  - One `TraceTurn` has many `TraceToolCall`.
  - One `TraceTurn` has many `TraceA2AInteraction`.
  - One `TraceTurn` has one-or-more `TraceSpanLink` for backend and frontend correlation.
- Validation rules:
  - `run_id` MUST be present when status is `completed` or `failed`.
  - `ended_at` MUST be present when status is `completed` or `failed`.

## Entity: TraceToolCall

- Description: Trace record for one tool invocation associated with a turn.
- Fields:
  - `tool_call_id` (string): AG-UI or runtime tool-call identifier.
  - `turn_id` (string, FK -> TraceTurn)
  - `tool_name` (string)
  - `started_at` (datetime)
  - `ended_at` (datetime | null)
  - `status` (enum): `started` | `completed` | `failed`.
  - `result_summary` (string | null)
  - `error_message` (string | null)
- Validation rules:
  - `tool_name` MUST be non-empty.
  - `tool_call_id` MUST be unique within a `turn_id`.

## Entity: TraceA2AInteraction

- Description: Trace record for one A2A exchange associated with a turn.
- Fields:
  - `a2a_interaction_id` (string)
  - `turn_id` (string, FK -> TraceTurn)
  - `source_agent` (string)
  - `target_agent` (string)
  - `operation_name` (string)
  - `started_at` (datetime)
  - `ended_at` (datetime | null)
  - `status` (enum): `started` | `completed` | `failed` | `timeout`.
  - `error_message` (string | null)
- Validation rules:
  - `source_agent` and `target_agent` MUST be non-empty.
  - `status=timeout` MUST include `ended_at`.

## Entity: TraceSpanLink

- Description: Correlation mapping between logical trace entities and OpenTelemetry span identifiers.
- Fields:
  - `entity_type` (enum): `conversation` | `turn` | `tool_call` | `a2a`.
  - `entity_id` (string)
  - `trace_id` (string)
  - `span_id` (string)
  - `parent_span_id` (string | null)
  - `service_name` (string)
  - `captured_at` (datetime)
- Validation rules:
  - `trace_id` and `span_id` MUST be present for every persisted link.
  - `entity_type + entity_id + span_id` MUST be unique.

## State Transitions

1. Conversation lifecycle:
   - `active` -> `completed` when all turns end without unrecovered errors.
   - `active` -> `failed` when unrecovered turn failures terminate the conversation.

2. Turn lifecycle:
   - `started` -> `completed` when assistant output and all required child operations finish.
   - `started` -> `failed` when model, tool, or A2A failure causes turn failure.

3. Tool call lifecycle:
   - `started` -> `completed` on successful result emission.
   - `started` -> `failed` on execution exception or explicit failure result.

4. A2A lifecycle:
   - `started` -> `completed` on successful downstream response.
   - `started` -> `failed` on downstream error.
   - `started` -> `timeout` on configured deadline expiration.
