# Quickstart: Execute Repository Stable Version Upgrade

## 1. Prepare workspace

```bash
cd /home/trniel/repos/nexus
```

## 2. Inventory current dependency baselines

```bash
# Python manifests
rg --files -g '**/pyproject.toml'

# Node manifests
rg --files -g '**/package.json'
```

## 3. Upgrade backend Python scopes

```bash
# API service
cd src/backend/api
uv lock --upgrade
uv sync --dev

# MCP service
cd ../mcp
uv lock --upgrade
uv sync --dev

# A2A service
cd ../agent-a2a
uv lock --upgrade
uv sync --dev
```

Compatibility notes:
- API currently uses `fastapi>=0.133.0,<0.133.1` due `agent-framework-ag-ui` constraint window.
- API telemetry stack aligns with `azure-monitor-opentelemetry` pinned instrumentation versions.
- A2A service currently uses `a2a-sdk>=0.3.25,<1.0.0` to preserve existing handler APIs.

## 4. Upgrade frontend Node scope

```bash
cd /home/trniel/repos/nexus/src/frontend
npm install
```

## 5. Apply Foundry-native client migration

- Update `src/backend/api/clients.py` to use `agent_framework.foundry.FoundryChatClient`.
- Keep `SupportsChatGetResponse` return contract unchanged.
- Preserve existing agent behavior in `src/backend/api/agents/logistics_agent.py`.

## 6. Validate quality gates

```bash
cd /home/trniel/repos/nexus
uv run --project . poe check

cd src/frontend
npm run lint
npm run build
```

Expected outcome:
- Python checks: all ruff and basedpyright checks pass across api/mcp/agent-a2a.
- Frontend checks: lint passes and Next.js production build completes.

## 7. Validate runtime and protocol behavior

```bash
cd /home/trniel/repos/nexus
npm run dev
```

- Confirm dashboard loads and chat works.
- Confirm filter tools and analysis flows remain functional.
- Confirm no AG-UI protocol regressions in tool call and state synchronization paths.

## 8. Produce release evidence

- Dependency version upgrade table per scope.
- Replacement/fork records for unsupported dependencies.
- Lockfile regeneration/transitive change summary.
- Validation results and regression gate evidence (100% pass on critical scenarios).
