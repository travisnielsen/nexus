# Tasks: Full Foundry V2 Tracing

**Input**: Design documents from `/specs/002-foundry-v2-tracing/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/tracing-compatibility-contract.md`, `quickstart.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare implementation validation artifacts and evidence paths.

- [X] T002 Create validation index and evidence tracker in `specs/002-foundry-v2-tracing/validation/README.md`
- [X] T003 [P] Create telemetry baseline inventory for current backend/frontend paths in `specs/002-foundry-v2-tracing/validation/telemetry-inventory.md`
- [X] T004 [P] Create baseline KQL/trace query pack for turn/tool/A2A checks in `specs/002-foundry-v2-tracing/validation/trace-baseline-kql.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement shared trace context primitives and cleanup guardrails required by all user stories.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T005 Create shared trace context model and propagation helpers in `src/backend/api/agents/utils/trace_context.py`
- [X] T006 Create shared telemetry attribute constants for conversation/turn/tool/A2A in `src/backend/api/agents/utils/telemetry_constants.py`
- [X] T006a Define Pydantic trace identity models (`conversation_id`, `turn_id`, `run_id`, `tool_call_id`, `a2a_interaction_id`) in `src/backend/api/agents/utils/trace_models.py`
- [X] T007 Wire AG-UI thread/run extraction and context seeding in `src/backend/api/main.py`
- [X] T008 Update observability bootstrap to enforce supported Foundry GenAI tracing gates in `src/backend/api/monitoring.py`
- [X] T009 [P] Document required tracing environment variables in `src/backend/api/.env.example`
- [X] T010 [P] Document required tracing environment variables in `src/backend/.env.example`
- [X] T011 Audit preview-era tracing/patch customizations and retirement decisions in `specs/002-foundry-v2-tracing/validation/preview-customization-audit.md`
- [X] T012 Apply safe patch toggle cleanup based on audit outcomes in `src/backend/api/patches/__init__.py`
- [X] T012a Enforce backend trace identity schema validation at ingress/egress in `src/backend/api/main.py` and `src/backend/api/agents/tools/trace_helpers.py`
- [X] T012b Define and enforce frontend TypeScript trace identity contracts in `src/frontend/src/lib/traceTypes.ts` and `src/frontend/src/app/api/copilotkit/[[...path]]/route.ts`

**Checkpoint**: Shared tracing foundation is ready; user story work can proceed.

---

## Phase 3: User Story 1 - View Complete Turn Traces (Priority: P1) 🎯 MVP

**Goal**: Ensure every conversation turn and its tool calls are consistently trace-visible and correlated in Foundry V2.

**Independent Test**: Run a multi-turn conversation with multiple tool calls and verify each turn and tool call can be inspected as correlated traces.

- [X] T013 [US1] Add per-turn lifecycle span boundaries for AG-UI runs in `src/backend/api/main.py`
- [X] T014 [P] [US1] Add stable agent/session trace attributes for orchestrator runs in `src/backend/api/agents/logistics_agent.py`
- [X] T015 [US1] Create reusable tool tracing helper for tool start/end/failure events in `src/backend/api/agents/tools/trace_helpers.py`
- [X] T016 [P] [US1] Instrument filter tool lifecycle spans using shared helper in `src/backend/api/agents/tools/filter_tools.py`
- [X] T017 [P] [US1] Instrument analysis tool lifecycle spans using shared helper in `src/backend/api/agents/tools/analysis_tools.py`
- [X] T018 [P] [US1] Instrument chart tool lifecycle spans using shared helper in `src/backend/api/agents/tools/chart_tools.py`
- [X] T019 [US1] Add turn/tool trace completeness validation script in `src/backend/api/scripts/validate_turn_traces.py`
- [X] T020 [US1] Document Foundry V2 turn/tool validation flow in `specs/002-foundry-v2-tracing/validation/us1-turn-tool-validation.md`
- [X] T020a [US1] Add AG-UI lifecycle compatibility validation (`RUN_*`, `TOOL_CALL_*`, state updates) in `specs/002-foundry-v2-tracing/validation/us1-agui-compatibility.md`
- [X] T020b [US1] Add CopilotKit thread continuity and New Chat behavior validation in `specs/002-foundry-v2-tracing/validation/us1-copilotkit-thread-validation.md`
- [X] T020c [US1] Add user-visible chat/tool behavioral regression checklist in `specs/002-foundry-v2-tracing/validation/us1-user-visible-regression.md`

**Checkpoint**: User Story 1 is independently functional and trace-visible.

---

## Phase 4: User Story 2 - Trace A2A Interactions Per Turn (Priority: P2)

**Goal**: Capture and correlate A2A interactions (success and failure) as child activities of the originating turn.

**Independent Test**: Trigger recommendation A2A flow and verify each A2A interaction appears under the correct turn trace with outcome metadata.

- [X] T021 [US2] Instrument outbound A2A request spans in recommendation flow in `src/backend/api/agents/tools/recommendation_tools.py`
- [X] T022 [US2] Propagate turn correlation metadata with outbound A2A requests in `src/backend/api/agents/tools/recommendation_tools.py`
- [X] T023 [US2] Instrument inbound A2A handling spans in `src/backend/agent-a2a/main.py`
- [X] T024 [P] [US2] Add explicit A2A trace attributes and status mapping in `src/backend/api/agents/utils/telemetry_constants.py`
- [X] T025 [US2] Add A2A failure and timeout trace semantics in `src/backend/agent-a2a/main.py`
- [X] T026 [US2] Document A2A trace validation and failure scenarios in `specs/002-foundry-v2-tracing/validation/us2-a2a-validation.md`

**Checkpoint**: User Stories 1 and 2 are independently functional with turn + A2A traceability.

---

## Phase 5: User Story 3 - Audit and Operate with Consistent Trace Coverage (Priority: P3)

**Goal**: Provide operational tooling and procedures to measure and review trace completeness over time.

**Independent Test**: Execute coverage checks across a recent conversation window and confirm measurable completeness output for turns/tools/A2A.

- [X] T027 [US3] Implement trace coverage query service functions with a default and validated minimum 24-hour review window in `src/monitoring/azure-dashboard/src/lib/logAnalyticsClient.ts`
- [X] T028 [P] [US3] Add trace coverage summary component in `src/monitoring/azure-dashboard/src/components/TraceCoverageSummary.tsx`
- [X] T029 [US3] Integrate coverage summary into dashboard shell in `src/monitoring/azure-dashboard/src/App.tsx`
- [X] T030 [US3] Add operational trace audit runbook for SC metrics in `specs/002-foundry-v2-tracing/validation/us3-trace-audit-runbook.md`
- [X] T031 [US3] Add SC-001/SC-002/SC-003 measurement report template in `specs/002-foundry-v2-tracing/validation/sc-measurement-template.md`
- [X] T031a [US3] Add 24-hour review-window boundary validation and evidence in `specs/002-foundry-v2-tracing/validation/us3-24h-window-validation.md`
- [X] T031b [US3] Add SC-004 incident drill protocol (5-minute failure-step identification target) in `specs/002-foundry-v2-tracing/validation/sc4-drill-protocol.md`
- [X] T031c [US3] Execute SC-004 drill and capture timing results in `specs/002-foundry-v2-tracing/validation/sc4-drill-results.md`

**Checkpoint**: All three user stories are independently functional and auditable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final hardening, docs alignment, and release evidence.

- [X] T001 Add final Microsoft Learn provenance appendix updates in `specs/002-foundry-v2-tracing/research.md`
- [X] T032 [P] Add GenAI tracing environment variable to Container App deployment config in `infra/workload.tf`
- [X] T033 [P] Align local/container tracing configuration guidance in `docker-compose.yml`
- [X] T034 [P] Update backend observability documentation with final tracing architecture in `src/backend/api/README.md`
- [X] T035 [P] Update monitoring guide with Foundry V2 validation workflow in `src/monitoring/README.md`
- [X] T036 Add SC-005 regression-rate comparison method and baseline window in `specs/002-foundry-v2-tracing/validation/sc5-regression-method.md`
- [X] T037 Produce SC-005 post-change failure-rate comparison report in `specs/002-foundry-v2-tracing/validation/sc5-regression-results.md`
- [X] T038 Execute quality gates and capture final pass/fail evidence checklist (required: quality-gate outputs, SC-001..SC-005 reports, AG-UI/CopilotKit compatibility evidence, 24-hour window validation) in `specs/002-foundry-v2-tracing/validation/final-quality-gate.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): No dependencies.
- Foundational (Phase 2): Depends on Setup; blocks all user story implementation.
- User Story phases (Phase 3-5): Depend on Foundational completion.
- Polish (Phase 6): Depends on all targeted user stories being complete.

### User Story Dependencies

- US1 (P1): Starts after Phase 2; no dependency on US2/US3.
- US2 (P2): Starts after Phase 2; can run in parallel with late US1 tasks, but requires US1 trace context primitives.
- US3 (P3): Starts after Phase 2; uses outputs from US1 and US2 validation data.

### Within Each User Story

- Establish correlation and instrumentation hooks before validation docs.
- Implement code changes before writing the story-specific validation evidence.
- Complete each story checkpoint before moving to polish.

### Parallel Opportunities

- Phase 1: T003 and T004.
- Phase 2: T009 and T010.
- US1: T014, T016, T017, T018 can run in parallel after T015.
- US2: T024 can run in parallel with T021-T023.
- US3: T028 can run in parallel with T027.
- Phase 6: T001 and T032-T037 can run in parallel before T038.

---

## Parallel Example: User Story 1

```bash
# After T015 completes, run tool module instrumentation in parallel:
Task: "T016 [US1] Instrument filter tool lifecycle spans using shared helper in src/backend/api/agents/tools/filter_tools.py"
Task: "T017 [US1] Instrument analysis tool lifecycle spans using shared helper in src/backend/api/agents/tools/analysis_tools.py"
Task: "T018 [US1] Instrument chart tool lifecycle spans using shared helper in src/backend/api/agents/tools/chart_tools.py"
```

## Parallel Example: User Story 2

```bash
# Run attribute schema and A2A instrumentation in parallel once outbound flow work starts:
Task: "T021 [US2] Instrument outbound A2A request spans in recommendation flow in src/backend/api/agents/tools/recommendation_tools.py"
Task: "T024 [US2] Add explicit A2A trace attributes and status mapping in src/backend/api/agents/utils/telemetry_constants.py"
```

## Parallel Example: User Story 3

```bash
# Build coverage backend query and UI summary concurrently:
Task: "T027 [US3] Implement trace coverage query service functions with a default and validated minimum 24-hour review window in src/monitoring/azure-dashboard/src/lib/logAnalyticsClient.ts"
Task: "T028 [US3] Add trace coverage summary component in src/monitoring/azure-dashboard/src/components/TraceCoverageSummary.tsx"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 and Phase 2.
2. Deliver Phase 3 (US1) and validate turn/tool completeness.
3. Demo Foundry V2 turn-level trace visibility as MVP outcome.

### Incremental Delivery

1. US1: turn + tool trace completeness.
2. US2: A2A trace completeness and failure visibility.
3. US3: operational auditability and measurable coverage reporting.
4. Polish: documentation, env alignment, and quality evidence.

### Team Parallelization

1. Shared team completes Phase 1-2.
2. One stream handles backend trace instrumentation (US1/US2).
3. One stream handles dashboard/reporting and ops artifacts (US3).
4. Merge in Phase 6 with final quality gate evidence.
