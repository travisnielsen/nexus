# Implementation Plan: Repository Stable Version Upgrade

**Branch**: `001-upgrade-stack-versions` | **Date**: 2026-05-29 | **Spec**: `specs/001-upgrade-stack-versions/spec.md`

**Input**: Feature specification from `specs/001-upgrade-stack-versions/spec.md`

## Summary

Upgrade all scoped backend and frontend components to current stable dependency versions while preserving existing behavior and protocol contracts. The backend chat client path is explicitly migrated to a Foundry-native client (`FoundryChatClient`) so the codebase is aligned with future Foundry v2 native/hosted capabilities, with architectural readiness for later `FoundryAgent` adoption where service-managed agents are desired.

## Technical Context

**Language/Version**:
- Python 3.12+ (`src/backend/api`, `src/backend/mcp`, `src/backend/agent-a2a`)
- TypeScript 5 + Node.js toolchain (`src/frontend`)

**Primary Dependencies**:
- Backend: FastAPI, Microsoft Agent Framework packages, Azure Identity, OpenTelemetry
- Agent runtime: move from legacy Azure compatibility client to `agent_framework.foundry.FoundryChatClient`
- Frontend: Next.js 16, React 19, CopilotKit, MSAL, AG-UI client

**Storage**:
- MCP service with DuckDB-backed interfaces and JSON source files; no new storage engines in scope

**Testing**:
- Python checks: `uv run --project . poe check`
- Frontend checks: `npm run lint`, `npm run build`
- Regression/smoke: dashboard + chat + tool call/state synchronization scenarios

**Target Platform**:
- Linux containerized services (Container Apps) and local Linux development

**Project Type**:
- Monorepo web application with Python backend services + Next.js frontend

**Performance Goals**:
- Maintain existing response and dashboard interaction behavior (no regression target from baseline)

**Constraints**:
- 100% pass on critical regression scenarios before release
- No bypass of MCP data path contracts
- Preserve AG-UI/CopilotKit compatibility
- Complete unsupported dependency replacement/forking within this feature

**Scale/Scope**:
- All manifests under `src/backend` and `src/frontend`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- [x] Data path integrity: feature keeps operational dashboard data on MCP-mediated paths.
- [x] No direct product-path SQL or Azure AI Search dependency introduced for core flight data.
- [x] Boundary contracts are explicitly typed and validated (Pydantic/TypeScript interfaces).
- [x] AG-UI + CopilotKit interaction compatibility is preserved and test coverage identified.
- [x] Quality gates and observability impact are captured (`uv run --project . poe check`, `npm run lint` for frontend changes, telemetry expectations for backend changes).

### Post-Design Re-Check

- [x] Research/design artifacts preserve MCP-mediated operational data flow.
- [x] Foundry-native client migration plan preserves typed chat client contract (`SupportsChatGetResponse`).
- [x] Contracts define AG-UI/CopilotKit compatibility invariants and validation requirements.
- [x] Quickstart includes required quality gates and regression validation.

## Project Structure

### Documentation (this feature)

```text
specs/001-upgrade-stack-versions/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── upgrade-compatibility-contract.md
└── tasks.md               # Created by /speckit.tasks
```

### Source Code (repository root)

```text
src/
├── backend/
│   ├── api/
│   │   ├── clients.py
│   │   ├── pyproject.toml
│   │   └── agents/
│   ├── mcp/
│   │   └── pyproject.toml
│   └── agent-a2a/
│       └── pyproject.toml
├── frontend/
│   ├── package.json
│   └── src/
```

**Structure Decision**: Keep existing monorepo structure; perform in-place dependency and client-factory upgrades without introducing new top-level modules.

## Phase Plan

### Phase 0: Research (Completed)

- Completed `research.md` with decisions for Foundry-native client migration, dependency policy, AG-UI compatibility, lockfile strategy, and unsupported package handling.
- Captured sources from:
  - MAF skill guidance
  - CopilotKit AG-UI code/docs MCP tools
  - Microsoft Learn MCP documentation (Foundry provider + migration notes)

### Phase 1: Design & Contracts (Completed)

- Completed `data-model.md` with upgrade entities and validation/state transitions.
- Completed contract definitions in `contracts/upgrade-compatibility-contract.md`.
- Completed execution and validation flow in `quickstart.md`.
- Planned context update in `.github/copilot-instructions.md` SPECKIT block to point to this plan.

### Phase 2: Implementation Planning (Completed)

- Generated `tasks.md` with ordered execution for:
  - Python dependency upgrades and lockfile regeneration
  - Node dependency upgrades and lockfile updates
  - `FoundryChatClient` migration in backend client factory
  - Regression and gate validation
  - Release evidence documentation

## Complexity Tracking

No constitution violations requiring exception handling.
