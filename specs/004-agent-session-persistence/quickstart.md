# Quickstart: Implement Agent Session Persistence

## 1. Prepare environment

1. From repository root, install dependencies and initialize local tooling:
   - `./devsetup.sh`
2. Ensure backend environment variables include Foundry endpoint/model and auth settings required by your local mode.
3. Start the monorepo runtime:
   - `npm run dev`

## 2. Validate existing continuity baseline

1. Open the app and confirm initial chat creates a `conv_*` ID via `POST /api/conversations`.
2. Confirm CopilotKit requests include `threadId` and backend traces contain matching `x-trace-conversation-id`.
3. Confirm `use_service_session=True` remains enabled in `src/backend/logistics/agents/logistics_agent.py`.

## 3. Implement backend session APIs

1. Add session models and validation schemas (list/load/rename/delete payloads and responses).
2. Add backend service methods for:
   - List latest 20 sessions (user-scoped, sorted by `last_activity_at` desc)
   - Load session transcript + restoration manifest
   - Rename session
   - Soft-delete session (product-level removal)
3. Add FastAPI endpoints under `src/backend/logistics/main.py` and enforce auth scope.
4. Keep Foundry conversation persistence as canonical transcript/context source.
5. Add idempotent Cosmos metadata bootstrap (create-if-not-exists for required database/container) owned by Logistics API.

## 4. Implement frontend history flyout and resume flow

1. Add a left-side flyout component displaying up to 20 sessions.
2. Implement localStorage-backed session cache (user-scoped keyspace) and hydrate from local cache at startup.
3. Bind row click to session load and thread switch using canonical session ID.
4. Add rename and delete actions with local-first UX and backend reconciliation.
5. Implement startup background sync and conflict reconciliation to backend-authoritative state.
6. Display pending/synced/failed sync status for local-first mutations.
7. Display per-entry date/time and unavailable-state labels.
8. Block session switching while active run is streaming unless canceled/completed.

## 5. Implement AG-UI artifact restoration subset

1. Define the v1 supported artifact subset and descriptor schema.
2. Rehydrate supported artifacts at their transcript positions during session load.
3. For unsupported or failed restorations, render transcript fallback notice without breaking resume.

## 6. Verify core scenarios

1. Sign in as a real user in local dev mode and run the lifecycle flow: create at least two conversations, send at least one user turn in each, refresh/reload the app, then reopen a prior session from history.
2. Resume a prior session and send a follow-up turn; verify continuity and context carryover.
3. Rename a session; refresh browser and verify durable rename.
4. Delete a session; verify removal from visible list and blocked reopen.
5. Load a session with supported artifact(s); verify restoration.
6. Load a session with unsupported artifact(s); verify transcript fallback messaging.
7. Validate unavailable session entry remains visible but blocked for resume.
8. Validate first-run environment auto-creates required Cosmos metadata resources.
9. Validate repeat startup/access path is idempotent and does not duplicate resources.
10. Validate startup local cache hydration occurs before backend sync round-trip.
11. Validate local-first rename/delete converges to backend-authoritative state with clear status indicators.
12. Measure SC-009 local feedback latency by capturing at least 20 rename/delete/open interactions and computing p95 from browser timestamps.
13. Measure SC-010 convergence by capturing at least 20 startup/mutation sync events and computing convergence duration p99 under normal local network.
14. Validate zero-turn conversations are not shown in session history after initial load before first user message.
15. Validate no-auth mode presents chat-only UX with no session history sidebar/actions.
16. Validate no-auth mode emits no session-history API calls (`/api/sessions/**`) using browser network capture and/or proxy request logs.
17. Validate operational flight data paths remain MCP-mediated after session persistence changes.

## 7. Run quality gates

1. Backend checks:
   - `uv run --project . poe check`
2. Frontend checks:
   - `cd src/frontend && npm run lint`
3. Run targeted integration checks for session API contracts and UI flows.

## 8. Capture release evidence

1. Session continuity validation report (thread/service_session_id/foundry conversation alignment).
2. Mutation durability report (rename/delete across refresh/device).
3. Artifact restoration coverage report (supported success + fallback behavior).
4. Authorization/privacy report proving no cross-user session access.
