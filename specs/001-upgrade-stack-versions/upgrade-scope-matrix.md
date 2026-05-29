# Upgrade Scope Matrix

Created: 2026-05-29

| Scope ID | Path | Ecosystem | Upgrade Type | Foundry/Protocol Impact |
|---|---|---|---|---|
| backend-api | src/backend/api | Python | Direct + transitive | High (MAF, Foundry client migration, AG-UI integration) |
| backend-mcp | src/backend/mcp | Python | Direct + transitive | Medium (MCP data-path integrity) |
| backend-a2a | src/backend/agent-a2a | Python | Direct + transitive | Medium (A2A compatibility) |
| frontend-app | src/frontend | Node/TypeScript | Direct + transitive | High (CopilotKit + AG-UI runtime compatibility) |

## Out of Scope

- `src/monitoring/azure-dashboard`

## Acceptance Mapping

- FR-001/FR-002: scope and dependency inventory covered by this matrix.
- FR-007: MCP path integrity validated in US2 validation tasks.
- FR-008: CopilotKit/AG-UI behavior validated in US2 validation tasks.
