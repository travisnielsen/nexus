# Implementation Plan: Agent Session Persistence

**Branch**: `004-agent-session-persistence` | **Date**: 2026-06-01 | **Spec**: `specs/004-agent-session-persistence/spec.md`

**Input**: Feature specification from `/specs/004-agent-session-persistence/spec.md`

## Summary

Implement a resumable session history experience that preserves the existing `conv_*` conversation-rooted linkage across CopilotKit, AG-UI, Microsoft Agent Framework (`use_service_session=True`), and Foundry Agent Service v2 persistence. The solution adds a left-side session flyout (latest 20 entries), localStorage-first session interactions for fast responsiveness, startup synchronization and reconciliation with backend APIs, session rename/delete flows, bounded AG-UI artifact rehydration, zero-turn session suppression in visible history, and no-auth chat-only gating (no history sidebar/actions) while preserving MCP-based operational data paths and current chat behavior for new conversations.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript 5 + React 19 + Next.js 16 (frontend)

**Primary Dependencies**: FastAPI, `agent-framework` (AgentFrameworkAgent + FoundryAgent + FoundryChatClient), CopilotKit React runtime, AG-UI protocol transport via `@ag-ui/client`, MSAL (`@azure/msal-browser`, `@azure/msal-react`), Pydantic boundary models

**Storage**: Foundry Agent Service v2 persistence (Cosmos-backed), feature-owned session metadata in Azure Cosmos DB deployed on a private VNET path and accessed only through Logistics API backend service interfaces, plus user-scoped browser localStorage cache for local-first session history UX

**Testing**: `uv run --project . poe check`, targeted backend API contract tests (pytest), frontend interaction tests for flyout and resume flows, `npm run lint`, and local authenticated end-to-end validation (sign in, create conversations, reload pages, reopen prior sessions) with browser network/trace evidence and manual AG-UI artifact restoration validation

**Target Platform**: Linux-hosted Azure Container Apps (backend/frontend), modern desktop-responsive web UI

**Project Type**: Monorepo web application with Python backend services + Next.js frontend

**Performance Goals**: Local session interactions (open/rename/delete UI response) should feel immediate and meet SC-009 measurement thresholds; startup/mutation sync convergence should meet SC-010 thresholds under normal network conditions; session list fetch should remain responsive for latest 20 sessions; rename/delete durable convergence should remain within acceptable UX bounds; resume path preserves continuity on first follow-up turn; no regression in active chat streaming responsiveness

**Constraints**:
- Preserve canonical `conversationId/threadId/service_session_id` continuity.
- Keep operational flight data access MCP-mediated (no direct product-path SQL/AI Search for dashboard data).
- Keep existing CopilotKit/AG-UI behavior for new chats and in-progress chats.
- Only latest 20 sessions are in scope for v1.
- Exclude zero-turn sessions from visible history until at least one persisted user message exists.
- In no-auth mode, expose chat-only UX and disable session history sidebar/actions and calls.
- Artifact rehydration is limited to a supported subset with transcript fallback.
- Session metadata Cosmos DB path remains private-network only and is not directly reachable from frontend clients.
- Session metadata backing resources require idempotent Logistics API bootstrap (create-if-not-exists) for first-run safety.
- Local cache is user-scoped and treated as a responsiveness layer only; backend APIs remain authoritative for durable state.

**Scale/Scope**: Frontend session flyout + chat resume wiring, backend session management APIs, session metadata persistence contract, AG-UI restoration policy, authorization enforcement, validation assets under `specs/004-agent-session-persistence/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate
- [x] Data path integrity: feature keeps operational dashboard data on MCP-mediated paths.
- [x] No direct product-path SQL or Azure AI Search dependency introduced for core flight data.
- [x] Boundary contracts are explicitly typed and validated (Pydantic/TypeScript interfaces).
- [x] AG-UI + CopilotKit interaction compatibility is preserved and test coverage identified.
- [x] Quality gates and observability impact are captured (`uv run --project . poe check`, `npm run lint` for frontend changes, telemetry expectations for backend changes).

### Post-Phase 1 Re-check
- [x] Data path integrity remains MCP-mediated for operational data.
- [x] Session APIs/contracts are typed and scoped to authenticated user identity.
- [x] AG-UI/CopilotKit compatibility and restoration fallback behavior are explicitly specified.
- [x] Quality gates, test strategy, and observability expectations are documented in quickstart/contracts.
- [x] No constitution violations require exception handling.

## Project Structure

### Documentation (this feature)

```text
specs/004-agent-session-persistence/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── session-persistence-api-contract.md
│   └── session-artifact-rehydration-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/frontend/
├── src/components/
│   ├── AuthenticatedCopilotKit.tsx
│   ├── NoAuthCopilotKit.tsx
│   └── [new] SessionHistoryFlyout.tsx
├── src/app/
│   ├── page.tsx
│   └── api/
│       ├── conversations/route.ts
│       └── copilotkit/[[...path]]/route.ts
└── src/lib/
    └── traceTypes.ts

src/backend/logistics/
├── main.py
├── clients.py
├── agents/
│   ├── logistics_agent.py
│   └── utils/
│       ├── trace_models.py
│       └── [new] session_models.py
└── [new] services/
    └── session_service.py

src/backend/logistics-data/
└── [no change to operational MCP data path]

specs/004-agent-session-persistence/
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

**Structure Decision**: Keep existing monorepo boundaries and add a dedicated session-management service layer inside `src/backend/logistics` for history listing, resume metadata, rename/delete mutations, and artifact restoration manifests. Frontend changes are constrained to CopilotKit wrapper state and a new flyout component, avoiding protocol-breaking changes to runtime route plumbing.

## Complexity Tracking

No constitution violations identified; section not applicable.
