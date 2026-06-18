# Implementation Plan: User Feedback Storage

**Branch**: `[005-user-feedback-storage]` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-user-feedback-storage/spec.md`

## Summary

Implement a unified feedback pipeline that captures turn-level and overall-experience feedback in authenticated mode, persists accepted submissions durably, and emits correlated telemetry for analytics and evaluation workflows. The approach extends the existing backend feedback endpoint into a typed, idempotent service boundary backed by Cosmos DB, adds explicit feedback-kind contracts for an emitted response-feedback card and AG-UI-invoked overall feedback card flows, and keeps CopilotKit plus AG-UI session continuity unchanged.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5 (frontend)

**Primary Dependencies**: FastAPI, Pydantic v2, Microsoft Agent Framework Python SDK, CopilotKit React Core and UI, AG-UI protocol integration, Azure Cosmos DB SDK, OpenTelemetry and Azure Monitor exporter

**Storage**: Azure Cosmos DB (durable feedback records; partitioned by conversation/session scope)

**Testing**: `uv run --project . poe check`, targeted backend unit/integration tests with `pytest`, frontend lint and interaction checks via `npm run lint` and existing app-level validation flows

**Target Platform**: Containerized Linux services (Azure Container Apps) and browser frontend (Next.js)

**Project Type**: Web application with Next.js frontend plus FastAPI backend and agent/tool integrations

**Performance Goals**:
- Preserve interactive feedback UX: immediate thumbs submission request dispatch on click
- Keep submission latency within existing chat interaction expectations (no visible chat interruption)
- Maintain retrieval filterability for analytics by session, turn, kind, rating, and time range

**Constraints**:
- Authenticated mode only for feedback capture
- Durable storage success is acceptance boundary; telemetry is best-effort with operator-visible failure state
- No change to canonical session identity (`conv_*`) or AG-UI/CopilotKit thread continuity contracts
- Must preserve MCP-only operational flight data path (no new direct product-path SQL/Azure AI Search dependency)

**Scale/Scope**:
- Feature scope: feedback capture pipeline for turn and overall kinds, durable persistence, telemetry correlation, and backend-admin queryability
- Query scope for first release: authorized backend or admin analytics consumers only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Data path integrity: feature keeps operational dashboard data on MCP-mediated paths.
- [x] No direct product-path SQL or Azure AI Search dependency introduced for core flight data.
- [x] Boundary contracts are explicitly typed and validated (Pydantic/TypeScript interfaces).
- [x] AG-UI + CopilotKit interaction compatibility is preserved and test coverage identified.
- [x] Quality gates and observability impact are captured (`uv run --project . poe check`, `npm run lint` for frontend changes, telemetry expectations for backend changes).

Post-Phase 1 re-check: PASS. The design artifacts in this plan package keep operational data concerns separated from feedback storage, define typed submission and retrieval contracts, preserve AG-UI/CopilotKit flow integrity for overall-feedback tool-call invocation, and include telemetry plus validation expectations.

## Project Structure

### Documentation (this feature)

```text
specs/005-user-feedback-storage/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
```text
src/backend/logistics/
├── main.py
├── monitoring.py
├── services/
│   ├── session_service.py
│   └── feedback_service.py              # new
├── agents/
│   ├── logistics_agent.py
│   └── tools/
│       └── feedback_tools.py            # new

src/frontend/
├── src/
│   ├── components/
│   │   ├── ResponseFeedbackCard.tsx     # new (emitted card for turn feedback)
│   │   └── OverallFeedbackCard.tsx      # new (emitted card for overall feedback)
│   ├── app/
│   │   └── page.tsx
│   └── lib/
│       └── logisticsTypes.ts
```

**Structure Decision**: Use the existing web-application split (`src/backend/logistics` plus `src/frontend`) and add a dedicated backend feedback service plus explicit emitted frontend feedback card components (`ResponseFeedbackCard` and `OverallFeedbackCard`). Keep feedback contracts in `specs/005-user-feedback-storage/contracts` and avoid introducing new top-level runtime services.

## Complexity Tracking

No constitution violations identified for this feature plan.
