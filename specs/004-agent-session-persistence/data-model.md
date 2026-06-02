# Data Model: Agent Session Persistence

## Entity: SessionSummary

- Description: User-visible history list row for one persisted conversation.
- Fields:
  - `session_id` (string): Canonical Foundry conversation ID (`conv_*`).
  - `title` (string): User-visible session name.
  - `title_source` (enum): `first_message` | `timestamp_fallback` | `user_edited`.
  - `last_activity_at` (datetime): Last turn timestamp used for sorting.
  - `created_at` (datetime): Session creation timestamp.
  - `availability` (enum): `available` | `unavailable`.
  - `has_user_turn` (bool): True when at least one persisted user message exists in Foundry Conversations items (`type=message`, `role=user`).
  - `is_deleted` (bool): Product-level soft deletion flag.
  - `deleted_at` (datetime | null): Soft deletion timestamp.
  - `artifact_support_state` (enum): `none` | `partial` | `supported_subset_present`.
- Relationships:
  - One `SessionSummary` maps to one `CanonicalSessionLinkage`.
  - One `SessionSummary` has one `SessionTranscript` and zero-or-more `SessionArtifact` records.
- Validation:
  - `title` must be non-empty and trimmed.
  - `has_user_turn=false` excludes item from visible history list responses.
  - `has_user_turn` is derived from Foundry Conversations API item retrieval rather than frontend-local state.
  - `availability=unavailable` blocks resume operations.
  - `is_deleted=true` excludes item from visible history list responses.

## Entity: CanonicalSessionLinkage

- Description: Alignment contract across frontend/backend/MAF/Foundry identity fields.
- Fields:
  - `session_id` (string): Canonical conversation ID.
  - `copilot_thread_id` (string): CopilotKit `threadId`.
  - `maf_service_session_id` (string): Agent Framework service session ID.
  - `foundry_conversation_id` (string): Foundry conversation identifier.
  - `last_verified_at` (datetime): Last successful continuity verification.
- Validation:
  - All identifier fields must be equal for a valid linkage in this feature.
  - Resume requests with mismatched IDs fail contract validation.

## Entity: SessionTranscript

- Description: Ordered user/assistant/tool transcript loaded during resume.
- Fields:
  - `session_id` (string, FK -> SessionSummary)
  - `messages` (array): Ordered transcript messages for rendered chat history.
  - `message_count` (int)
  - `loaded_at` (datetime)
  - `continuation_ready` (bool): True when next user turn can continue context.
- Validation:
  - `messages` ordering must be deterministic and stable by timestamp/sequence.
  - Transcript load succeeds even when artifact restoration is partial.

## Entity: SessionArtifact

- Description: Restorable non-text chat artifact tied to a transcript position.
- Fields:
  - `artifact_id` (string)
  - `session_id` (string, FK -> SessionSummary)
  - `message_id` (string): Parent transcript message.
  - `artifact_type` (string): AG-UI artifact type identifier.
  - `restoration_status` (enum): `restored` | `unsupported` | `missing_data` | `failed`.
  - `restoration_descriptor` (object | null): Minimal payload to re-render supported artifact.
  - `fallback_text` (string | null): User-visible transcript fallback note.
- Validation:
  - `restoration_descriptor` required when `restoration_status=restored`.
  - `fallback_text` required when restoration status is not `restored` and artifact was present.

## Entity: SessionMutation

- Description: Durable mutation record for rename/delete actions.
- Fields:
  - `mutation_id` (string)
  - `session_id` (string, FK -> SessionSummary)
  - `mutation_type` (enum): `rename` | `delete`.
  - `requested_by` (string): Authenticated user ID.
  - `requested_at` (datetime)
  - `applied_at` (datetime | null)
  - `status` (enum): `pending` | `applied` | `rejected`.
  - `conflict_reason` (string | null)
- Validation:
  - `requested_by` must match session ownership scope.
  - Delete mutation transitions session to `is_deleted=true` without requiring immediate Foundry hard delete.

## Entity: LocalSessionCacheSnapshot

- Description: Browser-local localStorage representation of session history for fast local-first interactions.
- Fields:
  - `user_cache_key` (string): User-scoped cache namespace key.
  - `sessions` (array[SessionSummary-lite]): Local session list snapshot.
  - `cache_version` (string): Schema version for migration safety.
  - `last_hydrated_at` (datetime): Last local cache read time.
  - `last_synced_at` (datetime | null): Last successful backend sync time.
- Validation:
  - Cache key must be user-scoped to avoid cross-user leakage.
  - Unsupported cache version triggers safe reset/rebuild from backend.

## Entity: SessionSyncOperation

- Description: Local queue/state entry for pending sync operations to backend.
- Fields:
  - `operation_id` (string)
  - `session_id` (string)
  - `operation_type` (enum): `rename` | `delete` | `load_hint`.
  - `local_applied_at` (datetime)
  - `sync_status` (enum): `pending` | `synced` | `failed`.
  - `last_error` (string | null)
- Validation:
  - Pending operations must be retried or resolved on startup sync.
  - Failed operations must surface user-visible status and reconciliation behavior.

## State Transitions

1. Session availability:
- `available` -> `unavailable` when backing history cannot be restored.
- `unavailable` -> `available` only when restore verification succeeds.

2. Session lifecycle (product visibility):
- `active` (implicit: `is_deleted=false`) -> `deleted` (`is_deleted=true`) after successful delete mutation.
- Deleted sessions are removed from list API responses but may remain platform-retained in Foundry.

3. Artifact restoration:
- `pending_evaluation` (implicit during load) -> `restored` when supported descriptor resolves.
- `pending_evaluation` -> `unsupported` for out-of-scope type.
- `pending_evaluation` -> `missing_data` when required payload no longer available.
- `pending_evaluation` -> `failed` on runtime restoration error.

4. Mutation processing:
- `pending` -> `applied` on durable backend commit.
- `pending` -> `rejected` on auth conflict, concurrency conflict, or validation failure.

5. Local cache lifecycle:
- `cold` (no cache) -> `hydrated_local` when localStorage snapshot is loaded at startup.
- `hydrated_local` -> `syncing` when backend synchronization begins.
- `syncing` -> `converged` when local snapshot and backend-authoritative state are reconciled.

6. Local mutation sync lifecycle:
- `pending` -> `synced` when backend mutation succeeds.
- `pending` -> `failed` when backend mutation fails; UI keeps failure marker until retry/reconcile.
