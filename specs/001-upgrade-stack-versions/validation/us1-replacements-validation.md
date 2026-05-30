# US1 Replacement and Compatibility Validation

Date: 2026-05-29

## Purpose

Validate functional equivalence for substitutions/caps required by ecosystem constraints during the stable-version upgrade.

## Replacements / Substitutions

1. Foundry client path replacement
- Original: agent_framework.azure.AzureAIClient
- Replacement: agent_framework.foundry.FoundryChatClient
- Validation:
  - `build_responses_client()` still returns SupportsChatGetResponse.
  - Async credential usage preserved (`azure.identity.aio.DefaultAzureCredential`).
  - Existing consumer contract in backend startup remains unchanged (`chat_client` wiring in main.py).

1. FastAPI compatibility cap
- Requested target: newest FastAPI stable line
- Constraint: `agent-framework-ag-ui==1.0.0rc3` requires `fastapi<0.133.1`
- Applied substitute: `fastapi>=0.133.0,<0.133.1`
- Validation:
  - API dependency resolution succeeded with this cap.
  - API lockfile regenerated successfully.

1. OpenTelemetry compatibility alignment
- Constraint: `azure-monitor-opentelemetry==1.8.8` pins `opentelemetry-instrumentation-fastapi==0.61b0`
- Applied substitute:
  - `opentelemetry-instrumentation-fastapi==0.61b0`
  - OTLP exporters aligned to `>=1.40.0,<1.41.0`
- Validation:
  - API dependency resolution succeeded.
  - API lockfile regenerated successfully.

1. ESLint major compatibility cap
- Requested target: newest ESLint stable (10.x)
- Constraint: `eslint-config-next@16.2.6` peer dependencies currently support eslint up to 9.x
- Applied substitute: `eslint^9.39.4`
- Validation:
  - Frontend dependency installation succeeded without peer-conflict warnings.
  - Frontend lockfile regenerated successfully.

1. A2A SDK service compatibility cap (recommendations project)
- Requested target: newest A2A SDK stable line (1.x)
- Constraint: current `src/backend/recommendations/main.py` implementation uses pre-1.0 API symbols/import paths
- Applied substitute: `a2a-sdk[http-server]>=0.3.25,<1.0.0`
- Validation:
  - Monorepo Python check passes (ruff + basedpyright) for `src/backend/recommendations`.
  - Service lockfile regenerated successfully.

## Equivalence Assessment

- Behavioral contract: preserved for agent/client integration path.
- Tool and session wiring: unaffected by this change set.
- Dependency graph: resolves cleanly across all scoped projects after replacements.

## Follow-up

- Revisit capped substitutions when upstream compatibility windows expand:
  - FastAPI beyond 0.133.x for agent-framework-ag-ui
  - ESLint 10 support in eslint-config-next
