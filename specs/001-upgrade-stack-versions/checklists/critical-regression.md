# Critical Regression Scenario Checklist

Created: 2026-05-29

## Backend

- [ ] API boots successfully with upgraded dependencies.
- [ ] Agent runtime initializes with Foundry-native chat client.
- [ ] Tool invocations complete without runtime serialization errors.
- [ ] MCP-backed data retrieval endpoints respond correctly.

## Frontend

- [ ] Application boots and renders dashboard and chat UI.
- [ ] CopilotKit runtime proxy route functions correctly.
- [ ] AG-UI tool call streaming events are handled without regression.
- [ ] Filter and analysis flows remain functional.

## Cross-System

- [ ] Thread/session continuity works with `use_service_session=True`.
- [ ] No regressions in core dashboard/chat user journeys.
- [ ] No new blocking errors in telemetry-instrumented backend flows.
