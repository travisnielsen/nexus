# Tasks: Agent Session Persistence

**Input**: Design documents from `/specs/004-agent-session-persistence/`

**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Validation MUST include local end-to-end runs in authenticated mode (sign in, create conversations, reload pages, reopen prior sessions) plus quality gates and captured evidence.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create feature scaffolding and shared interfaces used by all stories.

- [X] T001 Create session feature module scaffolding in `src/backend/logistics/services/session_service.py`
- [X] T002 Create session boundary models in `src/backend/logistics/agents/utils/session_models.py`
- [X] T003 [P] Create frontend session client utilities in `src/frontend/src/lib/sessionApi.ts`
- [X] T004 [P] Create frontend session state hook in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T005 [P] Define browser localStorage session cache key strategy in `src/frontend/src/lib/sessionCache.ts`
- [X] T062 [P] Add feature validation index document in `specs/004-agent-session-persistence/validation/validation-index.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement core backend/frontend foundations that block all user stories.

**CRITICAL**: No user story implementation begins until this phase is complete.

- [X] T006 Implement canonical session linkage validators in `src/backend/logistics/agents/utils/session_models.py`
- [X] T007 Implement session metadata repository/service abstraction in `src/backend/logistics/services/session_service.py`
- [X] T008 Add backend session list/load/rename/delete route shells in `src/backend/logistics/main.py`
- [X] T009 [P] Add Next.js session proxy endpoint for collection operations in `src/frontend/src/app/api/sessions/route.ts`
- [X] T010 [P] Add Next.js session proxy endpoint for item operations in `src/frontend/src/app/api/sessions/[sessionId]/route.ts`
- [X] T011 Add authorization and ownership enforcement for session APIs in `src/backend/logistics/main.py`
- [X] T012 Add typed unavailable/blocked/error response contracts in `src/backend/logistics/agents/utils/session_models.py`
- [X] T013 Wire session history context provider into authenticated wrapper in `src/frontend/src/components/AuthenticatedCopilotKit.tsx`
- [X] T014 Gate no-auth wrapper to chat-only mode (no session history sidebar/provider/actions) in `src/frontend/src/components/NoAuthCopilotKit.tsx`
- [X] T015 Implement Cosmos DB metadata bootstrap (create-if-not-exists for database/container) in `src/backend/logistics/services/session_service.py`
- [X] T016 Add backend startup/first-use initialization wiring for idempotent metadata bootstrap in `src/backend/logistics/main.py`
- [X] T017 Implement frontend local cache adapter (load/save/migrate) in `src/frontend/src/lib/sessionCache.ts`
- [X] T018 Implement startup sync orchestration shell in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T061 Implement Foundry Conversations API transcript reader (items.list + normalization) in `src/backend/logistics/services/session_service.py`

**Checkpoint**: Foundation complete; user story tasks can start.

---

## Phase 3: User Story 1 - Resume Prior Session (Priority: P1) 🎯 MVP

**Goal**: Users can browse recent sessions, load one, and continue with preserved context/linkage.

**Independent Test**: Open flyout, select an existing session, verify transcript loads, send follow-up, and confirm conversation continues in the same canonical session.

- [X] T019 [P] [US1] Implement session history flyout UI shell in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [X] T020 [US1] Implement latest-20 session query in backend service in `src/backend/logistics/services/session_service.py`
- [X] T021 [US1] Implement session list API response mapping in `src/backend/logistics/main.py`
- [X] T064 [US1] Exclude zero-turn sessions from history list query/results in `src/backend/logistics/services/session_service.py`
- [X] T022 [P] [US1] Render date/time and availability chips in flyout entries in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [X] T023 [US1] Hydrate session list from localStorage at startup in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T024 [US1] Implement startup background sync and reconciliation with backend list API in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T025 [US1] Implement session selection and load trigger in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T026 [US1] Implement transcript load + canonical linkage verification in `src/backend/logistics/services/session_service.py`
- [X] T027 [US1] Apply loaded session thread switching in authenticated flow in `src/frontend/src/components/AuthenticatedCopilotKit.tsx`
- [X] T029 [US1] Block session switching during active run and show blocked state in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T030 [US1] Show unavailable-session non-resumable UX state in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [ ] T031 [US1] Record US1 resume validation evidence in `specs/004-agent-session-persistence/validation/us1-resume-prior-session.md`

**Checkpoint**: US1 is independently functional and validates canonical resume continuity.

---

## Phase 4: User Story 2 - Manage Session List (Priority: P2)

**Goal**: Users can rename and delete sessions with durable backend persistence.

**Independent Test**: Rename and delete from flyout, refresh app, and verify durable updated history state.

- [X] T032 [P] [US2] Implement default title derivation helper in `src/backend/logistics/services/session_service.py`
- [X] T033 [US2] Ensure title generation on first display in session list mapping in `src/backend/logistics/main.py`
- [X] T034 [US2] Implement rename mutation handler and conflict outcomes in `src/backend/logistics/services/session_service.py`
- [X] T035 [US2] Implement delete (soft-hide) mutation handler in `src/backend/logistics/services/session_service.py`
- [X] T036 [P] [US2] Add rename interaction UI and inline editing state in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [X] T037 [P] [US2] Add delete interaction UI and confirmation state in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [X] T038 [US2] Apply rename locally first with pending sync state in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T039 [US2] Apply delete locally first with pending sync state in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T040 [US2] Reconcile local-first rename/delete outcomes with backend mutation APIs in `src/frontend/src/lib/useSessionHistory.ts`
- [X] T041 [US2] Implement durable mutation API handlers in `src/backend/logistics/main.py`
- [ ] T042 [US2] Record US2 mutation durability evidence in `specs/004-agent-session-persistence/validation/us2-session-management.md`

**Checkpoint**: US1 and US2 both work independently with durable backend-mediated mutations.

---

## Phase 5: User Story 3 - Restore Rich Chat Artifacts (Priority: P3)

**Goal**: Supported AG-UI artifacts rehydrate on resume, unsupported artifacts fall back safely.

**Independent Test**: Reopen sessions with supported and unsupported artifacts; verify restored subset and transcript-safe fallback behavior.

- [X] T043 [P] [US3] Define supported artifact subset schema in `src/backend/logistics/agents/utils/session_models.py`
- [X] T044 [US3] Implement artifact restoration manifest builder in `src/backend/logistics/services/session_service.py`
- [X] T045 [US3] Include aggregate restoration status in load API payload in `src/backend/logistics/main.py`
- [X] T046 [P] [US3] Implement frontend artifact hydrator utility in `src/frontend/src/lib/sessionArtifactHydration.ts`
- [X] T047 [US3] Render restored artifacts at transcript positions in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [X] T048 [US3] Render unsupported/missing artifact fallback notices in `src/frontend/src/components/SessionHistoryFlyout.tsx`
- [X] T049 [US3] Ensure restoration avoids replaying side effects in `src/frontend/src/lib/sessionArtifactHydration.ts`
- [X] T050 [US3] Record US3 artifact restoration evidence in `specs/004-agent-session-persistence/validation/us3-artifact-rehydration.md`

**Checkpoint**: All user stories are independently functional with restoration fallback safety.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, compatibility checks, docs, and quality gates.

- [X] T051 [P] Update backend service README for new session endpoints in `src/backend/logistics/README.md`
- [X] T052 [P] Update frontend integration notes for local-first session UX in `src/frontend/README.md`
- [ ] T053 Validate AG-UI/CopilotKit compatibility and document outcomes in `specs/004-agent-session-persistence/validation/us-cross-agui-compatibility.md`
- [ ] T054 Validate authorization/privacy isolation outcomes in `specs/004-agent-session-persistence/validation/us-cross-authz-privacy.md`
- [ ] T055 Validate private VNET Cosmos boundary (Logistics API-only access) in `specs/004-agent-session-persistence/validation/us-cross-network-boundary.md`
- [ ] T056 Validate create-if-not-exists bootstrap behavior in `specs/004-agent-session-persistence/validation/us-cross-cosmos-bootstrap.md`
- [ ] T057 Validate local-first startup hydration and reconciliation behavior in `specs/004-agent-session-persistence/validation/us-cross-local-cache-sync.md`
- [ ] T063 Validate transcript reload source contract (Foundry Conversations API only; no raw Cosmos transcript parsing) in `specs/004-agent-session-persistence/validation/us-cross-transcript-source-contract.md`
- [ ] T065 Validate zero-turn suppression in session history (fresh load + immediate history open) in `specs/004-agent-session-persistence/validation/us-cross-zero-turn-filter.md`
- [ ] T066 Validate no-auth mode hides session history sidebar/actions and emits no session-history API calls in `specs/004-agent-session-persistence/validation/us-cross-noauth-history-gating.md`
- [ ] T067 Validate MCP operational data-path integrity remains unchanged by session persistence feature in `specs/004-agent-session-persistence/validation/us-cross-mcp-path-integrity.md`
- [ ] T068 Validate authenticated local end-to-end session lifecycle (sign in, create conversations, reload, reopen prior sessions) in `specs/004-agent-session-persistence/validation/us-cross-local-auth-e2e.md`
- [ ] T069 Capture SC-009 and SC-010 metrics (local UI feedback latency + startup/mutation sync convergence) with measurement method and sample set in `specs/004-agent-session-persistence/validation/us-cross-performance-sync-metrics.md`
- [X] T058 Run backend quality gate and capture output in `specs/004-agent-session-persistence/validation/quality-gates.md`
- [X] T059 Run frontend lint gate and capture output in `specs/004-agent-session-persistence/validation/quality-gates.md`
- [ ] T060 Summarize success-criteria evidence (SC-001..SC-012) in `specs/004-agent-session-persistence/validation/final-quality-gate.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies; starts immediately.
- Foundational (Phase 2): Depends on Setup completion; blocks all user stories.
- User Stories (Phase 3-5): Depend on Foundational completion.
- Polish (Phase 6): Depends on desired user stories being complete.

### User Story Dependencies

- US1 (P1): Starts after Foundational; no dependency on other user stories.
- US2 (P2): Starts after Foundational; uses US1 flyout/state primitives but remains independently testable.
- US3 (P3): Starts after Foundational; can build on US1 load path while remaining independently testable.

### Suggested Story Completion Order

1. US1 -> 2. US2 -> 3. US3

---

## Parallel Execution Examples

### User Story 1

- Execute T019 and T020 in parallel (frontend flyout shell and backend list query).
- Execute T022 and T026 in parallel after T021 (UI chips and transcript/linkage logic).

### User Story 2

- Execute T036 and T037 in parallel (rename and delete UI interactions).
- Execute T034 and T035 in parallel (backend rename/delete handlers).

### User Story 3

- Execute T043 and T046 in parallel (backend subset schema and frontend hydrator utility).
- Execute T047 and T048 in parallel after T045 (restored rendering and fallback rendering).

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) only.
3. Validate resume continuity and canonical linkage before expanding scope.

### Incremental Delivery

1. Deliver US1 (resume continuity).
2. Deliver US2 (rename/delete durability).
3. Deliver US3 (artifact rehydration subset + fallback).
4. Finish cross-cutting validation and quality gates.

### Parallel Team Strategy

1. Team completes Setup + Foundational together.
2. Then split by story:
   - Engineer A: US1
   - Engineer B: US2
   - Engineer C: US3
3. Merge at Phase 6 for shared validation artifacts.
