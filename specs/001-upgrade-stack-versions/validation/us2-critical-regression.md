# US2 Critical Regression Gate Re-Run

Date: 2026-05-29

## Objective

Re-run critical regression checklist and determine gate status after upgrade/remediation.

## Environment

- MCP service running on http://localhost:8001
- A2A service running on http://localhost:5002
- API service running on http://localhost:8000
- Frontend dev server running on http://localhost:3000
- API auth disabled for local smoke checks (`AUTH_ENABLED=false`)

## Scenario Results

### Backend

- PASS: API boots successfully with upgraded dependencies.
  - Evidence: API startup logs show successful initialization and Uvicorn running.
- PASS: Agent runtime initializes with Foundry-native chat client.
  - Evidence: `Building FoundryChatClient` and `/logistics` endpoint registration logged on startup.
- PASS: Tool invocations complete without runtime serialization errors.
  - Evidence: successful chat turns execute tool calls and stream responses; filter and analysis tools update UI state as expected.
- PASS: MCP-backed data retrieval endpoints respond correctly.
  - Evidence:
    - `GET /api/flights` on MCP returns flight payload.
    - `GET /logistics/data/flights` on API returns proxied flight payload.

### Frontend

- PASS: Application boots and renders dashboard/chat UI.
  - Evidence: frontend route `/` returns HTTP 200 and page assets load.
  - Limitation: non-blocking CORS warning from CopilotKit announcement fetch (`cdn.copilotkit.ai`) may appear in local browser console.
- PASS: CopilotKit runtime proxy route functions correctly.
  - Evidence: route now serves both flat and catch-all paths, and `GET /api/copilotkit/threads` returns 200.
- PASS: AG-UI tool call streaming events are handled without regression.
  - Evidence: chat request streams tool execution and assistant response without `agent_connect_failed`/`agent_run_failed_event` errors.
- PASS: Filter and analysis flows remain functional.
  - Evidence: "Show over-utilized flights" applies active filter and updates table; follow-up analysis returns summarized metrics.

### Cross-System

- PASS: Thread/session continuity works with `use_service_session=True`.
  - Evidence: repeated successful `POST /api/conversations` responses with `conv_*` IDs.
- PASS: No regressions in core dashboard/chat user journeys.
  - Evidence: end-to-end conversation + tool + clear/reset interactions complete successfully in browser validation.
- PASS: No new blocking errors in telemetry-instrumented backend startup path.
  - Evidence: backend telemetry initializes and service boots with instrumentation enabled.

## Gate Status

- Critical regression gate: 100% PASS
- Current outcome: PASS after remediating frontend AG-UI client/runtime version mismatch.

## Required Action To Reach 100%

1. Monitor CopilotKit/AG-UI dependency alignment during future upgrades (keep `@ag-ui/client` aligned with CopilotKit package dependency set).
