# Implementation Plan: Full Foundry V2 Tracing

**Branch**: `002-foundry-v2-tracing` | **Date**: 2026-05-29 | **Spec**: `specs/002-foundry-v2-tracing/spec.md`

**Input**: Feature specification from `/specs/002-foundry-v2-tracing/spec.md`

## Summary

Implement full, end-to-end tracing visibility per conversation turn in Foundry V2 using currently supported Foundry-native SDK and Application Insights techniques, while preserving existing AG-UI/CopilotKit behavior and MCP-mediated operational data paths. The design emphasizes trace correlation consistency across frontend thread context, backend orchestration, tool execution, and A2A interactions, and includes removal planning for obsolete preview-era telemetry customizations where they are no longer required.

## Technical Context

**Language/Version**:
- Python 3.12+ (backend services)
- TypeScript 5 / Next.js 16 (frontend AG-UI proxy and runtime wiring)

**Primary Dependencies**:
- `agent-framework-core`, `agent-framework-ag-ui`, `agent-framework-foundry`
- `azure-ai-projects`, `azure-monitor-opentelemetry`
- `opentelemetry-*` 1.40 / 0.61b0 aligned stack
- `@copilotkit/runtime`, `@ag-ui/client`

**Storage**:
- Azure Application Insights + connected Log Analytics for trace storage/query
- No new operational data store; MCP remains operational data source

**Testing**:
- `uv run --project . poe check`
- `npm run lint` (frontend)
- End-to-end trace validation scenarios across `/api/copilotkit` -> `/logistics` -> tool calls -> A2A

**Target Platform**:
- Linux local development and Azure Container Apps deployment

**Project Type**:
- Monorepo web application with Python backend services and Next.js frontend

**Performance Goals**:
- Preserve current user-visible latency characteristics with telemetry overhead bounded and observable
- Achieve trace completeness metrics from spec success criteria (SC-001 through SC-003)

**Constraints**:
- Must use currently supported Foundry-native tracing techniques and AI SDK guidance
- Must preserve AG-UI event semantics and CopilotKit thread continuity
- Must not bypass MCP data contracts for operational flight data
- Must remove or simplify obsolete preview-era telemetry hooks when safe

**Scale/Scope**:
- In scope: `src/backend/logistics`, `src/backend/recommendations`, frontend CopilotKit proxy paths, monitoring docs/contracts
- Out of scope: redesign of business tools, MCP data model, and non-tracing product features

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate

- [x] Data path integrity: feature keeps operational dashboard data on MCP-mediated paths.
- [x] No direct product-path SQL or Azure AI Search dependency introduced for core flight data.
- [x] Boundary contracts are explicitly typed and validated (Pydantic/TypeScript interfaces).
- [x] AG-UI + CopilotKit interaction compatibility is preserved and test coverage identified.
- [x] Quality gates and observability impact are captured (`uv run --project . poe check`, `npm run lint`, telemetry validation expectations).

### Post-Design Re-Check

- [x] Research/design artifacts preserve MCP-mediated operational data flow.
- [x] Design defines typed boundary contracts for turn/tool/A2A trace identifiers.
- [x] Design keeps AG-UI/CopilotKit behavioral compatibility as a hard constraint.
- [x] Quickstart includes quality gates and trace-completeness validation steps.

## Project Structure

### Documentation (this feature)

```text
specs/002-foundry-v2-tracing/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── tracing-compatibility-contract.md
└── tasks.md                 # Created later by /speckit.tasks
```

### Source Code (repository root)

```text
src/
├── backend/
│   ├── api/
│   │   ├── main.py
│   │   ├── monitoring.py
│   │   ├── clients.py
│   │   ├── agents/
│   │   │   ├── logistics_agent.py
│   │   │   └── tools/
│   │   └── patches/
│   └── recommendations/
│       └── main.py
├── frontend/
│   └── src/
│       ├── app/api/copilotkit/[[...path]]/route.ts
│       ├── app/api/conversations/route.ts
│       └── components/
└── monitoring/
    ├── README.md
    └── azure-dashboard/
```

**Structure Decision**: Keep current monorepo shape and deliver tracing via targeted updates to existing backend/frontend observability paths rather than introducing new services.

## Phase Plan

### Phase 0: Research (Completed)

- Completed `research.md` with decisions on:
  - Foundry-native tracing strategy for app-owned AG-UI runtime
  - Turn/tool/A2A correlation design
  - Preview-era telemetry customization retirement candidates
  - Cadence reference adaptations for this repo
- Sources include:
  - MAF skill docs (`.github/skills/microsoft-agent-framework/*`)
  - CopilotKit/AG-UI MCP tools (`mcp_copilotkit_mc_search-ag-ui-docs`, `mcp_copilotkit_mc_search-ag-ui-code`)
  - Microsoft first-party docs (Microsoft Learn pages fetched for Agent Framework observability and Foundry tracing)
  - Reference repo: `travisnielsen/cadence` backend patterns
- Note: final source-provenance appendix polishing is tracked as a Phase 6 cross-cutting task and does not change research decisions.

### Phase 1: Design & Contracts (Completed)

- Completed `data-model.md` with trace entities and correlation relationships.
- Completed `contracts/tracing-compatibility-contract.md` with boundary and compatibility guarantees.
- Completed `quickstart.md` with validation and execution sequence.
- Updated `.github/copilot-instructions.md` SPECKIT plan reference to this plan.

### Phase 2: Implementation Planning (Ready)

- Ready for `/speckit.tasks` to generate dependency-ordered execution tasks.

## Complexity Tracking

No constitution violations require exemptions.
