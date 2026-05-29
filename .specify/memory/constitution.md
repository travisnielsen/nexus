<!--
Sync Impact Report
- Version change: N/A -> 1.0.0
- Modified principles:
	- N/A (initial adoption)
- Added sections:
	- Core Principles
	- Technology Stack
	- Development Workflow
	- Governance
- Removed sections:
	- None
- Templates requiring updates:
	- ✅ .specify/templates/plan-template.md
	- ✅ .specify/templates/spec-template.md
	- ✅ .specify/templates/tasks-template.md
	- ✅ .specify/extensions/git/commands/*.md (reviewed, no change required)
	- ✅ .specify/templates/commands/*.md (not applicable for Spec Kit 0.8.13 + copilot integration)
- Follow-up TODOs:
	- None
-->

# Nexus Constitution

## Core Principles

### I. MCP as the Operational Data Source (NON-NEGOTIABLE)

All operational flight and utilization data used by product features MUST flow through
the MCP service contracts (REST endpoints and MCP tools/resources). Feature work MUST NOT
introduce direct application-level dependencies on ad hoc SQL stores or Azure AI Search
for the primary dashboard data path. Rationale: this repository centralizes data access in
MCP to keep behavior deterministic, testable, and consistent across frontend and agents.

### II. Contract-Validated Agent Boundaries

All boundary payloads MUST be validated at ingress and egress with explicit schemas
(Pydantic for Python services and typed interfaces for TypeScript clients). Raw, unvalidated
dict/object contracts at service boundaries are prohibited. Rationale: validated boundaries
reduce silent failures in AG-UI and A2A flows and keep tool interactions predictable.

### III. Async, Typed, and Observable Services

I/O-bound backend operations MUST be asynchronous, function signatures MUST be fully typed,
and request/tool execution paths MUST emit structured telemetry through the existing
OpenTelemetry/Application Insights integration. Rationale: async correctness, type safety,
and traceability are required for reliable multi-service agent behavior.

### IV. CopilotKit + AG-UI Interaction Integrity

Conversational UI features MUST preserve CopilotKit and AG-UI protocol compatibility,
including tool-call semantics, thread continuity, and explicit state synchronization rules.
Changes that bypass these contracts MUST include a documented compatibility rationale and
tests for user-visible behavior. Rationale: the user experience depends on stable frontend
agent protocol integration.

### V. Automated Quality Gates Before Merge

Changes MUST pass the repository quality gates before merge: monorepo backend checks via
`uv run --project . poe check` and frontend linting via `npm run lint` when frontend files
are touched. Security and style checks configured in local hooks/CI MUST NOT be bypassed.
Rationale: automated gates prevent regressions and maintain code quality in mixed Python and
TypeScript services.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12+, FastAPI, Microsoft Agent Framework |
| Frontend | Next.js 16, React 19, CopilotKit, Tailwind CSS |
| AI Platform | Microsoft Foundry (Azure AI Foundry) |
| Data | MCP server (DuckDB-backed service interfaces) |
| Protocols | AG-UI (frontend-agent), A2A (agent-agent), MCP (data access) |
| Auth | Entra ID via MSAL and FastAPI middleware (optional in local dev) |
| Infrastructure | Terraform + Azure Container Apps |

## Development Workflow

1. Work from feature branches and use Conventional Commit formatting.
2. Run quality gates before commit and before PR updates for touched areas.
3. Include a constitution check in every plan and document any justified exceptions.
4. For data-impacting features, verify data flow remains MCP-mediated and does not add
   direct SQL/Azure AI Search product-path dependencies.
5. Keep prompts, tools, and UI behavior aligned: update related docs/tests when protocol
   contracts or agent behavior change.

## Governance

This constitution is the top-level engineering policy for this repository. Implementation
details belong in repository guidance such as CONTRIBUTING.md, media/docs/coding-standard.md,
media/docs/getting-started.md, and .github/copilot-instructions.md.

### Amendment Procedure

Any amendment MUST:
1. Use explicit normative language (MUST/SHOULD with rationale).
2. Update the Sync Impact Report at the top of this file.
3. Propagate aligned updates to affected templates and runtime guidance docs in the same
   change.

### Versioning Policy

Constitution versions follow semantic versioning:

- MAJOR: backward-incompatible governance changes or principle removals/redefinitions.
- MINOR: new principles/sections or materially expanded requirements.
- PATCH: clarifications, wording fixes, and non-semantic refinements.

### Compliance Review Expectations

Every planning cycle MUST include a constitution check. Any violation MUST be documented
with the reason, impact, and a simpler rejected alternative.

**Version**: 1.0.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-05-29
