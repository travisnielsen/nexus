# Tasks: Private Networking

**Input**: Design documents from `/specs/003-private-networking/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: No new automated test suite was explicitly requested in the spec. Validation tasks are included as implementation checks.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare authoritative inputs and baseline structure before infrastructure changes.

- [X] T001 Revalidate Azure private networking assumptions using available first-party Azure documentation sources (prefer `mcp_azure_mcp_documentation` when available, otherwise Microsoft Learn) and update provenance in specs/003-private-networking/research.md
- [X] T002 Mirror Cadence Terraform file layout scaffold in infra/networking.tf, infra/security.tf, infra/ai-platform.tf, infra/compute.tf, infra/devops.tf, infra/observability.tf, infra/utility.tf, infra/locals.shared.tf
- [X] T003 [P] Create variable sync script scaffold in infra/scripts/update-github-vars-from-terraform.sh
- [X] T004 [P] Add sync-script usage placeholder sections in infra/README.md and media/docs/dev-setup.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish shared Terraform and CI/CD foundations that block all user stories.

**CRITICAL**: No user story implementation starts before this phase is complete.

- [X] T005 Migrate common providers/state/shared locals from infra/main.tf and infra/workload.tf into infra/providers.tf and infra/locals.shared.tf
- [X] T006 Reorganize baseline variables and outputs into infra/variables.tf and infra/outputs.tf preserving current output contracts
- [X] T007 Update workflow variable references for renamed services in .github/workflows/deploy-logistics.yml, .github/workflows/deploy-logistics-data.yml, .github/workflows/deploy-recommendations.yml, and .github/workflows/deploy-frontend.yml
- [X] T040 Remove Azure Static Website dashboard deployment workflow from active CI/CD references and verify .github/workflows/deploy-dashboard.yml remains absent
- [X] T042 Add explicit outbound egress baseline resources for NAT Gateway (gateway + public IP/prefix) in infra/networking.tf and infra/security.tf
- [X] T008 Implement Terraform output-to-GitHub mapping definition in infra/scripts/update-github-vars-from-terraform.sh and supporting docs in infra/README.md
- [X] T009 Add idempotent dry-run and diff reporting behavior to infra/scripts/update-github-vars-from-terraform.sh
- [X] T010 Add Foundry-client-migration variable updates to sync map in infra/scripts/update-github-vars-from-terraform.sh and document required variables in .github/copilot-instructions.md
- [X] T011 Run baseline quality checks and record results in specs/003-private-networking/quickstart.md (`terraform fmt`, `terraform validate`, `uv run --project . poe check`)
- [X] T034 Build a service-boundary validation matrix from specs/003-private-networking/contracts/networking-and-exposure-contract.md and specs/003-private-networking/contracts/terraform-output-github-variable-sync-contract.md in specs/003-private-networking/quickstart.md

**Checkpoint**: Foundation ready - user story work can proceed.

---

## Phase 3: User Story 1 - Private Service Connectivity Baseline (Priority: P1) 🎯 MVP

**Goal**: Deliver private connectivity for Cosmos DB and Foundry with VNET-integrated runtime placement.

**Independent Test**: Deploy private networking changes and validate private endpoint + VNET-injected connectivity without requiring public data-plane access.

- [X] T012 [US1] Move virtual network and subnet definitions into infra/networking.tf following Cadence domain conventions
- [X] T013 [US1] Implement Cosmos DB private endpoint and private DNS bindings in infra/security.tf and infra/networking.tf
- [X] T014 [US1] Implement Foundry private endpoint inbound controls in infra/ai-platform.tf
- [X] T015 [US1] Implement Foundry outbound VNET injection configuration in infra/ai-platform.tf and infra/networking.tf
- [X] T016 [US1] Move/adjust logistics-data private dependency wiring to Cadence-aligned files in infra/compute.tf and infra/ai-platform.tf
- [X] T043 [US1] Associate NAT Gateway with applicable workload subnets requiring public endpoint egress in infra/networking.tf
- [X] T017 [US1] Add utility VM infrastructure in infra/utility.tf with operational-only access profile
- [X] T018 [US1] Document private endpoint DNS and validation runbook steps in infra/README.md and media/docs/getting-started.md
- [X] T035 [US1] Execute and record FR-011 service-boundary validation evidence (connectivity, ingress policy, and identity assumptions across logistics, logistics-data, recommendations, Foundry, and Cosmos DB) in specs/003-private-networking/quickstart.md
- [X] T036 [US1] Verify FR-009 MCP-mediated operational data path invariance after networking changes and capture evidence in specs/003-private-networking/quickstart.md

**Checkpoint**: US1 is deployable and private-dependency connectivity can be validated independently.

---

## Phase 4: User Story 2 - Controlled Public Exposure (Priority: P2)

**Goal**: Keep only frontend and logistics public while all other services remain private.

**Independent Test**: Validate ingress exposure matrix by service after deployment.

- [X] T019 [US2] Configure Container Apps environment VNET integration and ingress defaults in infra/networking.tf and infra/compute.tf
- [X] T020 [US2] Enforce public ingress only for frontend and logistics in infra/compute.tf
- [X] T021 [US2] Enforce internal-only ingress for logistics-data and recommendations in infra/compute.tf
- [X] T022 [US2] Keep ACR public network access enabled for public runner compatibility in infra/security.tf
- [X] T044 [US2] Validate and enforce ingress/egress split: frontend and logistics ingress public, internal services private, required public endpoint outbound routed via NAT egress in infra/compute.tf and specs/003-private-networking/quickstart.md
- [X] T023 [US2] Update deployment and operations docs for exposure model and ACR prerequisite in infra/README.md, README.md, and media/docs/dev-setup.md

**Checkpoint**: US2 can be validated independently with public/private endpoint checks by service.

---

## Phase 5: User Story 3 - Maintainable Terraform and Delivery Pipeline (Priority: P3)

**Goal**: Mirror Cadence structure authoritatively and keep CI/CD + variable sync operational.

**Independent Test**: Public-runner deployment pipeline runs successfully with synced variables and Cadence-aligned file organization.

- [X] T024 [US3] Complete remaining resource migration from infra/workload.tf into infra/networking.tf, infra/security.tf, infra/ai-platform.tf, infra/compute.tf, infra/devops.tf, infra/observability.tf, and infra/utility.tf
- [X] T025 [US3] Minimize legacy aggregators by reducing infra/workload.tf and infra/main.tf to only compatibility stubs or removing obsolete content
- [X] T041 [US3] During migration, retain dashboard static website module/outputs without structural relocation in 003 scope and document dashboard workflow retirement rationale in specs/003-private-networking/research.md
- [X] T026 [US3] Add script usage, permissions, and troubleshooting documentation for variable sync in infra/README.md and media/docs/getting-started.md
- [X] T027 [US3] Add CI/CD operator workflow for syncing variables before deployments in media/docs/dev-setup.md
- [X] T028 [US3] Validate sync script against live Terraform outputs and capture sample diff/report behavior in specs/003-private-networking/quickstart.md
- [X] T029 [US3] Align repo guidance with Cadence-authoritative structure decision and AVM precedence rule in .github/copilot-instructions.md and specs/003-private-networking/research.md
- [X] T037 [US3] Add before/after Terraform parity checklist for FR-008 and SC-005 (including allowed deltas and output diff evidence) in specs/003-private-networking/quickstart.md
- [X] T038 [US3] Add and execute SC-004 operator drill (locate and update correct Terraform concern area within 5 minutes) and record timing evidence in specs/003-private-networking/quickstart.md
- [X] T039 [US3] Define reliability evidence collection workflow for SC-003 and SC-008 (window, data source, and acceptance log format) in specs/003-private-networking/quickstart.md
- [X] T045 [US3] Add NAT egress operator guidance (design intent, destination scope, troubleshooting) in infra/README.md and media/docs/getting-started.md

**Checkpoint**: US3 is independently complete with maintainable structure and reproducible delivery workflow.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, verification, and release readiness across all stories.

- [X] T030 [P] Run full formatting and validation pass (`terraform fmt`, `terraform validate`) across infra/
- [X] T031 Run monorepo quality gates and record outcomes in specs/003-private-networking/quickstart.md (`uv run --project . poe check`, `npm run lint` if applicable)
- [X] T032 [P] Verify all impacted docs are updated (SC-009) in README.md, infra/README.md, media/docs/dev-setup.md, media/docs/getting-started.md, and .github/copilot-instructions.md
- [X] T033 Validate no AG-UI/CopilotKit behavior regression assumptions were violated and record evidence in specs/003-private-networking/quickstart.md
- [ ] T046 [P] Validate SC-011 by recording outbound verification evidence that required public endpoint calls egress through NAT Gateway in specs/003-private-networking/quickstart.md
  - Blocked pending deployed-environment runtime evidence capture (NAT Gateway path verification cannot be closed from design-time Terraform-only validation).

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): starts immediately.
- Foundational (Phase 2): depends on Setup completion and blocks all user stories.
- User Stories (Phases 3-5): depend on Foundational completion; execute in priority order for MVP, or parallel by staffing.
- Polish (Phase 6): depends on desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: starts after Phase 2; no dependency on other stories.
- **US2 (P2)**: starts after Phase 2; can proceed independently but benefits from US1 networking baseline.
- **US3 (P3)**: starts after Phase 2; depends on structural groundwork and can run partly in parallel with US2.

### Within Each User Story

- Infrastructure/domain file moves before policy hardening.
- Policy hardening before documentation finalization.
- Documentation before story checkpoint validation.

### Parallel Opportunities

- T003 and T004 can run in parallel.
- T030 and T032 can run in parallel.
- After Phase 2, US2 and US3 tasks that do not touch the same Terraform files can run in parallel.

---

## Parallel Example: User Story 2

```bash
# Parallelize ingress and ACR work once environment integration is ready:
Task: "T020 [US2] Enforce public ingress only for frontend and logistics in infra/compute.tf"
Task: "T022 [US2] Keep ACR public network access enabled for public runner compatibility in infra/security.tf"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1).
3. Validate private connectivity and utility VM readiness.
4. Pause for review/demo.

### Incremental Delivery

1. Deliver US1 private connectivity baseline.
2. Deliver US2 ingress/public exposure controls.
3. Deliver US3 Cadence-authoritative structure finalization + variable synchronization workflow.
4. Execute polish and release checks.

### Parallel Team Strategy

1. One engineer: foundational Terraform refactor + private networking.
2. One engineer: sync script + CI/CD variable workflow.
3. One engineer: documentation and operator runbooks.
4. Converge in Phase 6 for validation and cleanup.

---

## Notes

- Tasks intentionally include explicit file paths for direct execution.
- AVM guidance is applied only where compatible with Cadence-authoritative structure decisions.
- If `mcp_azure_mcp_documentation` access remains unavailable, maintain Microsoft Learn references and document that provenance in `research.md`.
- Azure Static Website dashboard deployment workflow is retired in this refactor, while dashboard static website infrastructure resources remain out of scope for 003 migration/restructure tasks.
