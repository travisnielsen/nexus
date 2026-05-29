# US1 Runtime Upgrade Outcomes

Date: 2026-05-29

## Scope

- API service: src/backend/api/pyproject.toml, src/backend/api/uv.lock
- MCP service: src/backend/mcp/pyproject.toml, src/backend/mcp/uv.lock
- A2A service: src/backend/agent-a2a/pyproject.toml, src/backend/agent-a2a/uv.lock
- Frontend app: src/frontend/package.json, src/frontend/package-lock.json
- Foundry client migration: src/backend/api/clients.py

## Authoritative Sources Used

- Microsoft Learn Agent Framework provider docs:
  - https://learn.microsoft.com/agent-framework/agents/providers/microsoft-foundry#create-an-agent-with-%60foundrychatclient%60
  - https://learn.microsoft.com/agent-framework/agents/#simple-agents-based-on-inference-services
- Microsoft Learn migration guidance:
  - https://learn.microsoft.com/azure/foundry-classic/how-to/prompt-flow-migration-overview#foundry-specific-considerations
- Package registries:
  - npm registry (npm view)
  - PyPI JSON API (https://pypi.org/pypi/{package}/json)

## Key Changes Completed

1. Upgraded backend direct dependencies across API/MCP/A2A manifests.
2. Upgraded frontend direct dependencies and dev dependencies.
3. Regenerated all scoped lockfiles:
   - src/backend/api/uv.lock
   - src/backend/mcp/uv.lock
   - src/backend/agent-a2a/uv.lock
   - src/frontend/package-lock.json
4. Migrated chat client factory to Foundry-native client:
   - from: agent_framework.azure.AzureAIClient
   - to: agent_framework.foundry.FoundryChatClient
5. Preserved SupportsChatGetResponse return contract and async credential flow.
6. Added compatibility env-var mapping in client factory (uses FOUNDRY_PROJECT_ENDPOINT/FOUNDRY_MODEL).

## Compatibility Blockers and Resolutions

- FastAPI latest conflict:
  - blocker: agent-framework-ag-ui 1.0.0rc3 requires fastapi <0.133.1
  - resolution: selected highest compatible stable fastapi range: >=0.133.0,<0.133.1
- OpenTelemetry conflict:
  - blocker: azure-monitor-opentelemetry 1.8.8 pins opentelemetry-instrumentation-fastapi ==0.61b0
  - resolution: aligned instrumentation/exporters to compatible 1.40/0.61b0 line
- Frontend ESLint major conflict:
  - blocker: eslint-config-next 16.2.6 peer support currently up to eslint 9
  - resolution: selected highest compatible stable eslint: ^9.39.4
- A2A SDK major compatibility conflict (agent-a2a service):
  - blocker: existing `src/backend/agent-a2a/main.py` targets pre-1.0 A2A SDK surface
  - resolution: selected latest known-compatible line for this service: `a2a-sdk>=0.3.25,<1.0.0`
- API async credential transport dependency:
  - blocker: API startup failed with `ImportError: aiohttp package is not installed`
  - resolution: restored explicit dependency `aiohttp>=3.13.2` in API manifest

## Validation Executed

- Lockfile regeneration succeeded for all scopes.
- Static diagnostics check on edited files reported no file-level errors.
- npm install completed with updated dependency graph and regenerated lockfile.

## Result

US1 runtime dependency upgrade and Foundry-native client migration are implemented with compatibility constraints documented and resolved.
