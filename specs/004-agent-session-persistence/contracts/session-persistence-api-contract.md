# Contract: Session Persistence API and Identity Continuity

## Purpose

Define required API and identity continuity behavior for session history listing, resume, rename, and delete across CopilotKit, backend, Agent Framework, and Foundry Agent Service v2.

## Contract 1: Session List

- Endpoint shape: backend provides a user-scoped list endpoint returning at most 20 sessions.
- Requirements:
  - Return newest-first ordering by `last_activity_at`.
  - Include `session_id`, `title`, `title_source`, `display_datetime`, `availability`.
  - Exclude zero-turn sessions (sessions without at least one persisted user message item from Foundry Conversations API, `type=message` and `role=user`).
  - Exclude product-deleted sessions (`is_deleted=true`).
  - Include unavailable sessions that are still user-visible (`availability=unavailable`).

## Contract 2: Session Load/Resume

- Endpoint shape: backend provides a load endpoint by `session_id`.
- Requirements:
  - Return transcript payload and restoration manifest.
  - Transcript retrieval MUST use supported Foundry Conversations APIs as the primary read contract.
  - Return canonical identity mapping where `session_id == copilot_thread_id == maf_service_session_id == foundry_conversation_id`.
  - If `availability=unavailable`, return a blocked resume response with explicit reason.
  - Successful load must allow immediate continuation turn in the same canonical session.

## Contract 10: Transcript Source Precedence and Schema Safety

- Requirements:
  - Primary source: Foundry Conversations API item/message retrieval for a given canonical conversation id.
  - Backend MUST normalize heterogeneous conversation items (message, function/tool call, function/tool output) into a stable transcript payload contract for frontend hydration.
  - Direct raw Cosmos document parsing for transcript reconstruction is out of scope for this feature and MUST NOT be used by session load endpoints.
  - Frontend MUST NOT depend on Foundry internal Cosmos container/document schema.

## Contract 11: Auth-Mode Gating for Session History

- Requirements:
  - Session history UI (sidebar/flyout and session actions) is available only in authenticated mode.
  - In no-auth mode, frontend MUST NOT render session history controls or invoke session list/load/rename/delete APIs.
  - Backend session history endpoints remain authorization-scoped and are not required for no-auth chat-only usage.

## Contract 3: Session Rename

- Endpoint shape: backend rename mutation endpoint accepts `session_id` + new `title`.
- Requirements:
  - Validate ownership and non-empty title.
  - Persist durable title update and return normalized session summary.
  - Conflict or authorization errors must return typed failure payloads for UI messaging.

## Contract 4: Session Delete (Product Visibility)

- Endpoint shape: backend delete mutation endpoint accepts `session_id`.
- Requirements:
  - Apply product-level soft delete (hide from session list and block resume).
  - Do not require immediate hard delete of Foundry backing records.
  - Return durable mutation status (`applied` or typed failure).

## Contract 5: Authorization and User Scope

- Requirements:
  - All session list/load/mutation operations are scoped to the authenticated user.
  - Cross-user access attempts must return authorization failure.
  - Session titles and metadata must not leak across user boundaries.

## Contract 6: Active Run Switching Safety

- Requirements:
  - If a run is active, session switch attempts must be blocked until run completion or explicit cancellation.
  - UI and backend response states must communicate blocked-switch reason deterministically.

## Contract 7: Private Network Persistence Boundary

- Requirements:
  - Session metadata persistence must use Azure Cosmos DB on a private VNET path.
  - Cosmos DB must be accessible only through the Logistics API backend path for this feature.
  - Frontend and chat clients must never access Cosmos DB directly.
  - All session list/load/mutation operations flow through backend APIs that enforce both auth scope and network boundary.

## Contract 8: Cosmos Bootstrap and Idempotent Provisioning

- Requirements:
  - Logistics API must perform idempotent create-if-not-exists initialization for required session metadata Cosmos DB resources.
  - Bootstrap behavior must safely handle already-existing database/container resources without destructive changes.
  - Missing required resources in a new environment must be created automatically during service initialization or first access path.
  - Bootstrap failures must return actionable backend diagnostics and keep request failures explicit.

## Contract 9: Local-First Session Cache and Sync

- Requirements:
  - Frontend must maintain a user-scoped localStorage session cache for immediate history interaction responsiveness.
  - App startup must hydrate from localStorage first, then synchronize with backend list/load APIs.
  - Rename/delete interactions must apply locally first with pending sync status and then invoke backend mutation APIs.
  - Reconciliation must converge to backend-authoritative durable state and provide deterministic conflict/failure handling.
  - Local cache keys must be scoped to user identity to prevent cross-user leakage on shared browsers.

## Validation Gates

- Required checks:
  - Identity continuity verification for resumed sessions.
  - Verification that session load transcript is derived from supported Foundry Conversations APIs.
  - Verification that frontend transcript hydration consumes backend-normalized payloads only (no direct Cosmos schema coupling).
  - Verification that session load code paths do not query raw Foundry Cosmos containers for transcript reconstruction.
  - Verification that zero-turn sessions are excluded from list responses.
  - Verification that no-auth mode renders without session history sidebar/actions and does not issue session history API calls (asserted by browser network capture and/or API proxy logs).
  - Verification that session persistence changes do not alter operational data access paths (operational flight data remains MCP-mediated).
  - List limit/order validation.
  - Rename/delete durability after page refresh.
  - Authorization tests for cross-user isolation.
  - Verification that no frontend route or client code performs direct Cosmos DB access.
  - Verification that first-run environment creates required metadata database/container via create-if-not-exists.
  - Verification that repeat startup/access does not duplicate or mutate existing Cosmos resources unexpectedly.
  - Verification that localStorage startup hydration occurs before backend sync.
  - Verification that local-first rename/delete operations reconcile to backend state with explicit pending/synced/failed outcomes.
