# Lockfile and Transitive Update Record

Created: 2026-05-29

## Recording Format

For each scope, capture:

- Scope ID
- Manifest path
- Lockfile path
- Command used
- Regenerated (yes/no)
- Direct dependency deltas (name: from -> to)
- Transitive changes count
- Notable conflict resolutions
- Validation references

## Scope Records

### backend-api
- Scope ID: backend-api
- Manifest: `src/backend/logistics/pyproject.toml`
- Lockfile: `src/backend/logistics/uv.lock`
- Command used: `uv lock --upgrade`
- Regenerated: yes
- Notable conflict resolutions:
  - FastAPI constrained to `>=0.133.0,<0.133.1` due `agent-framework-ag-ui` requirement window.
  - OpenTelemetry instrumentation aligned with `azure-monitor-opentelemetry==1.8.8`.
  - Restored `aiohttp` as explicit API dependency for async Azure credential transport.
- Validation references:
  - `specs/001-upgrade-stack-versions/validation/us1-runtime-upgrade.md`
  - `specs/001-upgrade-stack-versions/validation/us1-replacements-validation.md`

### backend-mcp
- Scope ID: backend-mcp
- Manifest: `src/backend/logistics-data/pyproject.toml`
- Lockfile: `src/backend/logistics-data/uv.lock`
- Command used: `uv lock --upgrade`
- Regenerated: yes
- Validation references:
  - `specs/001-upgrade-stack-versions/validation/us1-runtime-upgrade.md`

### backend-a2a
- Scope ID: backend-a2a
- Manifest: `src/backend/recommendations/pyproject.toml`
- Lockfile: `src/backend/recommendations/uv.lock`
- Command used: `uv lock --upgrade`
- Regenerated: yes
- Notable conflict resolutions:
  - `a2a-sdk` constrained to compatible `<1.0.0` line for existing recommendations runtime code.
- Validation references:
  - `specs/001-upgrade-stack-versions/validation/us1-runtime-upgrade.md`

### frontend-app
- Scope ID: frontend-app
- Manifest: `src/frontend/package.json`
- Lockfile: `src/frontend/package-lock.json`
- Command used: `npm install`
- Regenerated: yes
- Notable conflict resolutions:
  - ESLint held on compatible `9.x` major due current `eslint-config-next` peer support.
- Validation references:
  - `specs/001-upgrade-stack-versions/validation/us1-runtime-upgrade.md`
  - `specs/001-upgrade-stack-versions/validation/us1-replacements-validation.md`
