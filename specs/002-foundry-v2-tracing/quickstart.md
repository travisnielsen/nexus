# Quickstart: Plan and Validate Full Foundry V2 Tracing

## 1. Prepare environment

1. From repository root, ensure backend and frontend dependencies are installed.
2. Confirm Azure credentials and Foundry project configuration are available.
3. Confirm Application Insights resource is linked to the Foundry project and permissions are in place.

## 2. Confirm baseline runtime wiring

1. Start local services using existing development scripts.
2. Verify frontend chat requests flow through `/api/copilotkit` and backend `/logistics` endpoint.
3. Verify conversation bootstrap uses backend `/api/conversations`.

## 3. Enable and verify observability configuration

1. Enable backend instrumentation configuration.
2. Confirm Azure Monitor/Application Insights exporter configuration is active.
3. Confirm required GenAI tracing gate configuration is present for Foundry SDK tracing.
4. Trigger a sample conversation and verify traces appear in monitoring backends.

## 4. Validate turn, tool, and A2A coverage

1. Execute a conversation with multiple turns and at least one turn with multiple tool calls.
2. Execute a conversation that triggers A2A recommendation flow.
3. Verify each turn has corresponding trace coverage.
4. Verify each tool call and A2A interaction appears as correlated child activity under the originating turn.

## 5. Validate failure-path visibility

1. Trigger a controlled tool call failure.
2. Trigger a controlled A2A failure or timeout.
3. Verify failure status and diagnostic attributes are trace-visible and linked to the proper turn.

## 6. Validate AG-UI and user behavior compatibility

1. Verify normal chat experience and tool-triggered UI updates remain unchanged.
2. Verify thread continuity and new chat behavior continue to function as before.
3. Verify no regressions in MCP-backed data operations.

## 7. Quality gates

1. Run backend checks: `uv run --project . poe check`.
2. Run frontend checks when touched: `npm run lint`.
3. Record trace completeness metrics against SC-001, SC-002, and SC-003.

## 8. Produce release evidence

1. Capture sample trace correlation reports for successful turns.
2. Capture sample trace correlation reports for failed tool and A2A paths.
3. Document removed or retained telemetry customizations and rationale.
4. Confirm all acceptance scenarios from the feature spec are satisfied.
