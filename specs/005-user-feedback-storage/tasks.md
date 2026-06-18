# Tasks: User Feedback Storage

**Input**: Design documents from `/specs/005-user-feedback-storage/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: No explicit TDD or mandatory automated-test requirement was specified in the feature spec, so this task list focuses on implementation and scenario validation tasks.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Every task includes concrete file path(s)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish feature scaffolding across backend and frontend.

- [ ] T001 Add feedback feature configuration scaffold and constants in `src/backend/logistics/main.py`.
- [ ] T002 [P] Create backend feedback service module scaffold in `src/backend/logistics/services/feedback_service.py`.
- [ ] T003 [P] Extend frontend feedback type definitions for kind-based payloads in `src/frontend/src/lib/logisticsTypes.ts`.
- [ ] T004 [P] Add overall feedback UI component scaffold in `src/frontend/src/components/OverallFeedbackCard.tsx`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Complete core contracts, validation, persistence, telemetry, and agent wiring before story work.

**⚠️ CRITICAL**: No user-story implementation should begin until this phase is complete.
- [ ] T006 Implement shared feedback request and outcome validation models in `src/backend/logistics/main.py`.
- [ ] T042 Implement canonical session identifier enforcement for feedback submissions, accepting only the established conversation identifier shape and rejecting alternate parallel session keys in `src/backend/logistics/main.py` and `src/backend/logistics/services/feedback_service.py`.
- [ ] T007 [P] Implement deterministic idempotency key helpers in `src/backend/logistics/services/feedback_service.py`.
- [ ] T008 [P] Implement Cosmos container bootstrap and upsert primitives for feedback records in `src/backend/logistics/services/feedback_service.py`.
- [ ] T009 [P] Implement telemetry emission helper and outcome status mapping in `src/backend/logistics/services/feedback_service.py`.
- [ ] T046 Implement explicit Application Insights failure telemetry emission for Cosmos DB persistence failures (include `storage_error`, feedback correlation identifiers, and operator-diagnostic fields) in `src/backend/logistics/services/feedback_service.py`.
- [ ] T010 Wire authenticated feedback submission guard and dependency setup in `src/backend/logistics/main.py`.
- [ ] T011 Add backend feature-toggle plumbing for overall feedback flows in `src/backend/logistics/main.py`.
- [ ] T012 Create overall-feedback AG-UI tool scaffolding in `src/backend/logistics/agents/tools/feedback_tools.py`.
- [ ] T013 Register feedback tools in `src/backend/logistics/agents/tools/__init__.py` and `src/backend/logistics/agents/logistics_agent.py`.

**Checkpoint**: Foundation ready. User stories can now be implemented.

---

## Phase 3: User Story 1 - Capture Response Feedback (Priority: P1) 🎯 MVP

**Goal**: Capture immediate thumbs feedback for a specific assistant response with durable persistence and telemetry correlation.

**Independent Test**: Submit thumbs-up/down on an agent response and verify accepted submission, persisted record, and uninterrupted chat continuity.

### Implementation for User Story 1

- [ ] T014 [US1] Extend `POST /logistics/feedback` to process `turn_response` submissions in `src/backend/logistics/main.py`.
- [ ] T015 [P] [US1] Implement turn-response required-field validation (`conversation_id`, `turn_id`, `trace_id`, `rating`) in `src/backend/logistics/services/feedback_service.py`.
- [ ] T016 [P] [US1] Update emitted response-feedback card payload builder to send `feedback_kind` and `source_surface` in `src/frontend/src/components/ResponseFeedbackCard.tsx`.
- [ ] T017 [US1] Ensure emitted response-feedback card click dispatch is immediate and non-blocking for ongoing chat UX in `src/frontend/src/components/ResponseFeedbackCard.tsx`.
- [ ] T018 [US1] Persist and return accepted outcome envelope (`feedback_id`, `idempotency_key`, storage/telemetry status) in `src/backend/logistics/main.py` and `src/backend/logistics/services/feedback_service.py`.
- [ ] T019 [US1] Emit turn-feedback correlation telemetry fields for accepted submissions in `src/backend/logistics/services/feedback_service.py`.
- [ ] T041 [US1] Hide turn-response feedback controls when authentication is disabled by gating render paths in `src/frontend/src/components/ResponseFeedbackCard.tsx` and auth-aware chat state in `src/frontend/src/app/page.tsx`.
- [ ] T047 [US1] Render a clear, non-blocking user-facing failure message when feedback submission returns `accepted=false` with `storage_status=failed` using the existing React inline status pattern (component state + conditional render, no new notification dependency) and an accessible `aria-live` region in `src/frontend/src/components/ResponseFeedbackCard.tsx`.

**Checkpoint**: US1 is independently functional and validates MVP behavior.

---

## Phase 4: User Story 2 - Add Optional Context To Negative Feedback (Priority: P2)

**Goal**: Support optional inline comments for negative feedback and update the same logical feedback record.

**Independent Test**: Submit thumbs-down without comment, then add comment later for same response and verify single effective record is updated.

### Implementation for User Story 2

- [ ] T020 [US2] Implement latest-write-wins update semantics for negative feedback comment updates in `src/backend/logistics/services/feedback_service.py`.
- [ ] T021 [P] [US2] Wire comment-after-vote submission to reuse existing logical feedback key in `src/frontend/src/components/ResponseFeedbackCard.tsx`.
- [ ] T022 [US2] Implement dismiss-without-comment behavior while preserving rating-only state in `src/frontend/src/components/ResponseFeedbackCard.tsx`.
- [ ] T023 [US2] Enforce comment-as-submitted storage policy with payload validity checks in `src/backend/logistics/services/feedback_service.py`.
- [ ] T024 [US2] Return update-aware response metadata for repeated submissions in `src/backend/logistics/main.py`.

**Checkpoint**: US2 works independently and does not create duplicate logical feedback records.

---

## Phase 5: User Story 3 - Capture Overall Experience Feedback (Priority: P3)

**Goal**: Add overall experience feedback through the CopilotKit plus AG-UI tool-call chat flow with feature toggle control.

**Independent Test**: Trigger overall feedback affordance, verify in-chat card generated through AG-UI flow, submit feedback, and verify shared endpoint persistence.

### Implementation for User Story 3

- [ ] T025 [US3] Implement AG-UI tool for overall-feedback card invocation in `src/backend/logistics/agents/tools/feedback_tools.py`.
- [ ] T026 [US3] Register overall-feedback tool for agent execution in `src/backend/logistics/agents/tools/__init__.py` and `src/backend/logistics/agents/logistics_agent.py`.
- [ ] T027 [P] [US3] Implement overall feedback card UI and submit handler in `src/frontend/src/components/OverallFeedbackCard.tsx`.
- [ ] T028 [US3] Add chat affordance and feature-toggle-driven visibility in `src/frontend/src/app/page.tsx`.
- [ ] T029 [US3] Route overall card submission to shared feedback endpoint with `overall_experience` payload in `src/frontend/src/components/OverallFeedbackCard.tsx`.
- [ ] T030 [US3] Preserve optional `card_turn_id` association during overall feedback persistence mapping in `src/backend/logistics/services/feedback_service.py`.
- [ ] T031 [US3] Enforce toggle-off behavior to hide affordance and reject disabled-surface submissions in `src/frontend/src/app/page.tsx` and `src/backend/logistics/main.py`.
- [ ] T048 [US3] Render the same clear, non-blocking user-facing failure message for overall feedback submissions when `accepted=false` with `storage_status=failed` using the same inline React status pattern as US1 (no new notification dependency) and an accessible `aria-live` region in `src/frontend/src/components/OverallFeedbackCard.tsx`.

**Checkpoint**: US3 is independently functional with AG-UI-compliant invocation and toggle behavior.

---

## Phase 6: User Story 4 - Analyze Feedback By Session And Turn (Priority: P4)

**Goal**: Provide authorized backend or admin feedback retrieval with required filters and correlation fields.

**Independent Test**: Query feedback as authorized consumer with session, turn, kind, rating, and time filters; verify unauthorized access is denied.

### Implementation for User Story 4

- [ ] T032 [US4] Implement authorized feedback query endpoint and filter parameters in `src/backend/logistics/main.py`.
- [ ] T033 [P] [US4] Implement filtered query and pagination methods in `src/backend/logistics/services/feedback_service.py`.
- [ ] T034 [US4] Enforce backend or admin authorization policy for query access in `src/backend/logistics/main.py`.
- [ ] T035 [US4] Map query response fields to contract shape and preserve correlation fields in `src/backend/logistics/main.py`.
- [ ] T036 [US4] Add operational logging for storage-only and telemetry-only failure states in `src/backend/logistics/services/feedback_service.py`.

**Checkpoint**: US4 is independently functional with secure query access and analytics-ready filtering.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate end-to-end behavior, quality gates, and documentation updates.

- [ ] T037 [P] Update implementation notes and executed validation evidence in `specs/005-user-feedback-storage/quickstart.md`.
- [ ] T038 Run backend quality gates and address issues for changed feedback files using `uv run --project . poe check` from repository root.
- [ ] T039 Run frontend lint and address issues for changed feedback UI files using `npm run lint` in `src/frontend`.
- [ ] T040 Execute quickstart validation flows and record outcome summary in `specs/005-user-feedback-storage/quickstart.md`.
- [ ] T043 Define success-criteria evidence matrix and measurement method for SC-001 through SC-019 in `specs/005-user-feedback-storage/quickstart.md`.
- [ ] T044 Implement validation logging and counters needed to compute acceptance percentages and rejection/authorization outcomes in `src/backend/logistics/main.py`, `src/backend/logistics/services/feedback_service.py`, and `src/frontend/src/components/ResponseFeedbackCard.tsx`.
- [ ] T045 Execute and record threshold verification results for all measurable SC targets and attach pass/fail evidence in `specs/005-user-feedback-storage/quickstart.md`.
- [ ] T049 Validate and record user-visible save-failure behavior for both response-feedback and overall-feedback cards under simulated Cosmos DB write failure in `specs/005-user-feedback-storage/quickstart.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies, starts immediately.
- **Phase 2 (Foundational)**: Depends on Setup and blocks all user stories.
- **Phase 3-6 (User Stories)**: Depend on Foundational completion.
- **Phase 7 (Polish)**: Depends on completion of desired user stories.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; no dependency on other stories.
- **US2 (P2)**: Starts after Foundational and builds on US1 feedback record semantics.
- **US3 (P3)**: Starts after Foundational; independent from US2; shares endpoint with US1.
- **US4 (P4)**: Starts after Foundational; depends on persistence model from US1/US3 for meaningful data.

### Within Each User Story

- Backend validation and persistence path before UI wiring where applicable.
- Payload integration before UX refinements.
- Story-specific telemetry and contract conformance before checkpoint.

### Parallel Opportunities

- Setup tasks marked **[P]** can run in parallel.
- Foundational tasks **T007-T009** can run in parallel once model shape is agreed.
- In US1, backend and frontend payload tasks **T015/T016** can run in parallel.
- In US3, UI card implementation **T027** can run in parallel with backend tool registration **T025-T026**.
- In US4, query service implementation **T033** can run in parallel with endpoint scaffolding **T032**.

---

## Parallel Example: User Story 1

```bash
# Parallel backend/frontend work for US1
Task: T015 [US1] Implement turn-response validation in src/backend/logistics/services/feedback_service.py
Task: T016 [US1] Update thumbs payload in src/frontend/src/components/ResponseFeedbackCard.tsx
```

## Parallel Example: User Story 3

```bash
# Parallel AG-UI tool and UI card work for US3
Task: T025 [US3] Implement overall-feedback tool in src/backend/logistics/agents/tools/feedback_tools.py
Task: T027 [US3] Implement overall feedback card in src/frontend/src/components/OverallFeedbackCard.tsx
```

## Parallel Example: User Story 4

```bash
# Parallel query endpoint and service filtering work for US4
Task: T032 [US4] Implement query endpoint in src/backend/logistics/main.py
Task: T033 [US4] Implement filtered query methods in src/backend/logistics/services/feedback_service.py
```

---

## Implementation Strategy

### MVP First (US1)

1. Complete Phase 1 and Phase 2.
2. Complete US1 (Phase 3).
3. Validate immediate capture, durability, and no chat interruption.
4. Demo or ship MVP increment.

### Incremental Delivery

1. Add US2 for comment enrichment updates.
2. Add US3 for AG-UI overall feedback flow and feature toggle.
3. Add US4 for authorized analytics retrieval.
4. Complete Polish phase and quality-gate verification.

### Parallel Team Strategy

1. Team completes Setup and Foundational together.
2. After checkpoint:
- Developer A: US1 and US2
- Developer B: US3
- Developer C: US4
3. Rejoin for Phase 7 validation and quality gates.

---

## Notes

- All tasks follow required checklist format: `- [ ] Txxx [P?] [US?] Description with file path`.
- Story labels appear only on user-story phase tasks.
- Include constitution-aligned implementation checks for typed boundaries, AG-UI/CopilotKit compatibility, and quality gates.

---

## Appendix: Documentation Maintenance (Non-Blocking)

These tasks are documentation or reference updates that do not block user-story implementation.

- [ ] T005 Backfill Azure platform provenance note for feedback telemetry guidance in `specs/005-user-feedback-storage/research.md`.
