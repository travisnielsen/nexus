# Dependency Baseline Inventory

Created: 2026-05-29

## Scope

- Backend API: `src/backend/api/pyproject.toml`
- Backend MCP: `src/backend/mcp/pyproject.toml`
- Backend A2A: `src/backend/agent-a2a/pyproject.toml`
- Frontend: `src/frontend/package.json`

## Python Baseline (pre-upgrade)

### `src/backend/api/pyproject.toml`
- a2a-sdk: `<1.0.0`
- agent-framework-a2a: `>=1.0.0b260225`
- agent-framework-ag-ui: `>=1.0.0b260225`
- agent-framework-azure-ai: `>=1.0.0rc2`
- agent-framework-core: `>=1.0.0rc2`
- azure-ai-projects: `>=2.0.0b3`
- azure-identity: `>=1.15.0`
- fastapi: `>=0.110.0`
- uvicorn: `>=0.27.0`
- pydantic: `>=2.12.0`

### `src/backend/mcp/pyproject.toml`
- mcp: `>=1.25.0`
- httpx: `>=0.27.0,<1.0`
- uvicorn: `>=0.27.0`
- starlette: `>=0.40.0`
- duckdb: `>=1.0.0`
- pyjwt[crypto]: `>=2.8.0`
- cachetools: `>=5.3.0`

### `src/backend/agent-a2a/pyproject.toml`
- a2a-sdk[http-server]: `>=0.3.22,<1.0.0`
- fastapi: `>=0.110.0`
- uvicorn: `>=0.27.0`
- pydantic: `>=2.11.3`

## Node Baseline (pre-upgrade)

### `src/frontend/package.json`
- next: `^16.1.7`
- react: `^19.2.4`
- react-dom: `^19.2.4`
- @copilotkit/react-core: `^1.54.0`
- @copilotkit/react-ui: `^1.54.0`
- @copilotkit/runtime: `^1.54.0`
- @ag-ui/client (override): `0.0.46`
- @azure/msal-browser: `^5.5.0`
- @azure/msal-react: `^5.0.7`

## Notes

- This inventory captures declared direct dependency ranges before implementation changes.
- Lockfile state and transitive change deltas are tracked separately in `lockfile-update-records.md`.
