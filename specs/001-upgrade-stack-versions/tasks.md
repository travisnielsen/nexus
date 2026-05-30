# Tasks: Repository Stable Version Upgrade

**Input**: Design documents from `/specs/001-upgrade-stack-versions/`

**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`

**Tests**: Explicit new test authoring is not required by spec; validation and regression execution tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish upgrade execution artifacts and scope baselines.

- [X] T001 Create dependency baseline inventory in specs/001-upgrade-stack-versions/dependency-baseline.md
- [X] T002 Create scoped upgrade matrix in specs/001-upgrade-stack-versions/upgrade-scope-matrix.md
- [X] T003 [P] Create validation evidence index in specs/001-upgrade-stack-versions/validation-index.md
- [X] T004 [P] Add Foundry client migration checklist in specs/001-upgrade-stack-versions/foundry-migration-checklist.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared dependency policy, validation gates, and compatibility guardrails before story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Update dependency policy and unsupported-package replacement rules in specs/001-upgrade-stack-versions/research.md
- [X] T006 [P] Define release gate checklist in specs/001-upgrade-stack-versions/checklists/release-gate.md
- [X] T007 [P] Define critical regression scenario list in specs/001-upgrade-stack-versions/checklists/critical-regression.md
- [X] T008 [P] Document lockfile/transitive update recording format in specs/001-upgrade-stack-versions/lockfile-update-records.md
- [X] T009 Define Foundry environment variable compatibility mapping in specs/001-upgrade-stack-versions/contracts/foundry-client-config.md

**Checkpoint**: Foundation ready; user story implementation can begin.

---

## Phase 3: User Story 1 - Upgrade Runtime Dependencies Safely (Priority: P1) 🎯 MVP

**Goal**: Upgrade backend/frontend dependency stacks to latest stable-compatible versions and migrate the backend agent client path to Foundry-native `FoundryChatClient`.

**Independent Test**: Verify all scoped direct dependencies are upgraded/replaced appropriately, lockfiles regenerated, and runtime still boots with Foundry-native client wiring.

### Implementation for User Story 1

- [X] T010 [US1] Upgrade API service dependency declarations in src/backend/logistics/pyproject.toml
- [X] T011 [P] [US1] Upgrade MCP service dependency declarations in src/backend/logistics-data/pyproject.toml
- [X] T012 [P] [US1] Upgrade A2A service dependency declarations in src/backend/recommendations/pyproject.toml
- [X] T013 [P] [US1] Upgrade frontend app dependency declarations in src/frontend/package.json
- [X] T015 [US1] Regenerate API lockfile with transitive updates in src/backend/logistics/uv.lock
- [X] T016 [P] [US1] Regenerate MCP lockfile with transitive updates in src/backend/logistics-data/uv.lock
- [X] T017 [P] [US1] Regenerate A2A lockfile with transitive updates in src/backend/recommendations/uv.lock
- [X] T018 [P] [US1] Regenerate frontend lockfile with transitive updates in src/frontend/package-lock.json
- [X] T020 [US1] Migrate chat client factory to Foundry-native `FoundryChatClient` in src/backend/logistics/clients.py
- [X] T021 [US1] Preserve agent construction compatibility after client migration in src/backend/logistics/agents/logistics_agent.py
- [X] T022 [US1] Implement stable substitute or in-repo fork for unsupported dependencies in affected manifests and source files
- [X] T023 [US1] Record US1 dependency and lockfile outcomes in specs/001-upgrade-stack-versions/validation/us1-runtime-upgrade.md
- [X] T024 [US1] Validate replacement/fork functional equivalence and record outcomes in specs/001-upgrade-stack-versions/validation/us1-replacements-validation.md

**Checkpoint**: User Story 1 is complete and independently demonstrable.

---

## Phase 4: User Story 2 - Preserve Existing Product Behavior (Priority: P2)

**Goal**: Validate and preserve backend/frontend behavior and AG-UI/CopilotKit protocol compatibility after upgrades.

**Independent Test**: Run quality gates and critical regression scenarios; confirm 100% pass on critical scenarios and no protocol regressions.

### Implementation for User Story 2

- [X] T025 [US2] Update backend validation runbook for upgraded stack in specs/001-upgrade-stack-versions/quickstart.md
- [X] T026 [P] [US2] Verify AG-UI session and tool-call behavior compatibility in src/backend/logistics/patches/agui_event_stream.py
- [X] T027 [P] [US2] Verify CopilotKit runtime proxy compatibility in src/frontend/src/app/api/copilotkit/route.ts
- [X] T028 [US2] Execute monorepo Python quality gate and record results in specs/001-upgrade-stack-versions/validation/us2-python-checks.md
- [X] T029 [P] [US2] Execute frontend lint/build validation and record results in specs/001-upgrade-stack-versions/validation/us2-frontend-checks.md
- [X] T030 [US2] Identify and document upgrade compatibility regressions in specs/001-upgrade-stack-versions/validation/us2-regressions-found.md
- [X] T031 [US2] Apply compatibility remediations for any upgrade regressions in affected backend/frontend files
- [X] T032 [US2] Re-run critical regression checklist and record 100% gate status in specs/001-upgrade-stack-versions/validation/us2-critical-regression.md
- [X] T033 [US2] Verify MCP-mediated operational data path integrity in src/backend/logistics/agents/utils/mcp_client.py, src/backend/logistics/agents/utils/data_helpers.py, and src/backend/logistics-data/main.py; record evidence in specs/001-upgrade-stack-versions/validation/us2-mcp-data-path.md
- [X] T034 [US2] Validate typed service boundary contracts and document compatibility/versioning notes in specs/001-upgrade-stack-versions/validation/us2-boundary-contracts.md

**Checkpoint**: User Stories 1 and 2 are both independently functional and validated.

---

## Phase 5: User Story 3 - Provide Clear Upgrade Traceability (Priority: P3)

**Goal**: Produce complete traceability artifacts for dependency changes, replacements, validation evidence, and release readiness.

**Independent Test**: Review generated artifacts and confirm every scoped dependency has an explicit outcome and linked validation evidence.

### Implementation for User Story 3

- [ ] T035 [US3] Create consolidated dependency version record in specs/001-upgrade-stack-versions/dependency-version-record.md
- [ ] T036 [P] [US3] Create consolidated lockfile update record in specs/001-upgrade-stack-versions/lockfile-update-records.md
- [ ] T037 [P] [US3] Create dependency replacement record with owners/evidence in specs/001-upgrade-stack-versions/dependency-replacements.md
- [ ] T038 [US3] Create final upgrade summary report in specs/001-upgrade-stack-versions/upgrade-summary.md
- [ ] T039 [US3] Record release decision with critical-gate evidence in specs/001-upgrade-stack-versions/release-decision.md

**Checkpoint**: All user stories are complete with full traceability.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, documentation alignment, and end-to-end execution proof.

- [ ] T040 [P] Align plan/spec/research references with final artifacts in specs/001-upgrade-stack-versions/plan.md
- [ ] T041 [P] Update repository guidance with final plan reference in .github/copilot-instructions.md
- [ ] T042 Run full quickstart workflow and capture final execution log in specs/001-upgrade-stack-versions/validation/final-quickstart-run.md
- [ ] T043 Perform final artifact consistency review in specs/001-upgrade-stack-versions/tasks.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; starts immediately.
- **Phase 2 (Foundational)**: Depends on Setup; blocks all user story implementation.
- **Phase 3 (US1)**: Depends on Foundational completion.
- **Phase 4 (US2)**: Depends on US1 completion.
- **Phase 5 (US3)**: Depends on US1 and US2 evidence artifacts.
- **Phase 6 (Polish)**: Depends on all user stories complete.

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational; enables all subsequent validation and reporting.
- **US2 (P2)**: Starts after US1 dependency/client migration completion.
- **US3 (P3)**: Starts after US1/US2 to compile final outcomes and validation evidence.

### Within Each User Story

- Dependency declaration updates before lockfile regeneration.
- Client migration before behavior validation.
- Validation execution before release-gate decisions.
- Consolidated reporting after all validations complete.

## Parallel Opportunities

- Setup: T003, T004 can run in parallel.
- Foundational: T006, T007, T008 can run in parallel.
- US1: T011/T012/T013 and T016/T017/T018 can run in parallel after T010/T015 sequencing constraints.
- US2: T026, T027, T029, T030 can run in parallel; T032 depends on T031 completion.
- US3: T036 and T037 can run in parallel before T038.
- Polish: T040 and T041 can run in parallel.

## Parallel Example: User Story 1

```bash
# Parallel dependency declaration updates
T011 src/backend/logistics-data/pyproject.toml
T012 src/backend/recommendations/pyproject.toml
T013 src/frontend/package.json

# Parallel lockfile regenerations after dependency updates
T016 src/backend/logistics-data/uv.lock
T017 src/backend/recommendations/uv.lock
T018 src/frontend/package-lock.json
```

## Parallel Example: User Story 2

```bash
# Parallel protocol and frontend validations
T026 src/backend/logistics/patches/agui_event_stream.py
T027 src/frontend/src/app/api/copilotkit/route.ts
T029 specs/001-upgrade-stack-versions/validation/us2-frontend-checks.md
T030 specs/001-upgrade-stack-versions/validation/us2-regressions-found.md
```

## Parallel Example: User Story 3

```bash
# Parallel evidence aggregation tasks
T036 specs/001-upgrade-stack-versions/lockfile-update-records.md
T037 specs/001-upgrade-stack-versions/dependency-replacements.md
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 dependency upgrades, lockfile regeneration, and Foundry-native client migration.
3. Validate runtime boot and capture US1 evidence.

### Incremental Delivery

1. Deliver US1 as MVP (runtime upgrade and Foundry-native migration).
2. Deliver US2 with full quality and critical regression validation.
3. Deliver US3 with complete traceability and release artifacts.
4. Complete Polish phase and final quickstart run.

### Team Parallel Strategy

1. One stream handles Python scopes (API/MCP/A2A).
2. One stream handles frontend Node scope.
3. One stream handles validation evidence and release artifacts.
4. Merge at critical checkpoints (US1 complete, US2 gate pass, US3 report complete).

## Notes

- All tasks include explicit file paths.
- Story labels are used only in user story phases.
- Foundry-native migration is mandatory via T020 (`FoundryChatClient`).
- Critical regression release gate is enforced after remediation in T032 and documented for release in T039.
