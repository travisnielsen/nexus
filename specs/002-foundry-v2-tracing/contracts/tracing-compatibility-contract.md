# Contract: Foundry V2 Tracing Compatibility and Coverage

## Purpose

Define non-negotiable tracing, correlation, and compatibility guarantees for end-to-end conversation turn tracing in Foundry V2.

## Contract 1: Turn Trace Completeness

- In-scope paths:
  - `src/backend/logistics/main.py`
  - `src/frontend/src/app/api/copilotkit/[[...path]]/route.ts`
  - `src/frontend/src/components/NoAuthCopilotKit.tsx`
  - `src/frontend/src/components/AuthenticatedCopilotKit.tsx`
- Requirements:
  - Every completed conversation turn MUST map to at least one trace visible in Foundry V2.
  - Conversation and turn identifiers MUST be consistently present on emitted traces.
  - Missing turn traces MUST be detectable via validation queries/workflows.

## Contract 2: Tool Call Trace Coverage

- In-scope paths:
  - `src/backend/logistics/agents/tools/`
  - `src/backend/logistics/agents/logistics_agent.py`
- Requirements:
  - All tool calls executed during a turn MUST emit trace records linked to the parent turn.
  - Tool call failures MUST emit explicit failure status and error context.
  - Correlation keys (`turn_id`, `run_id`, `tool_call_id`) MUST be preserved across boundaries.

## Contract 3: A2A Interaction Trace Coverage

- In-scope paths:
  - `src/backend/logistics/agents/tools/recommendation_tools.py`
  - `src/backend/recommendations/main.py`
- Requirements:
  - All A2A interactions initiated during a turn MUST emit child trace spans linked to the originating turn.
  - A2A failures and timeouts MUST be trace-visible with actionable metadata.
  - Source and target agent identity MUST be represented in trace attributes.

## Contract 4: AG-UI and CopilotKit Behavioral Compatibility

- In-scope paths:
  - `src/frontend/src/app/api/copilotkit/[[...path]]/route.ts`
  - `src/backend/logistics/main.py`
  - `src/backend/logistics/patches/agui_event_stream.py`
- Requirements:
  - AG-UI event lifecycle semantics (`RUN_*`, `TOOL_CALL_*`, state updates) MUST remain compatible for existing UI behavior.
  - CopilotKit thread continuity behavior MUST remain functionally equivalent.
  - Tracing enhancements MUST NOT require users to change chat interaction patterns.

## Contract 5: MCP Data Path Integrity

- In-scope paths:
  - `src/backend/logistics/agents/utils/mcp_client.py`
  - `src/backend/logistics/agents/utils/data_helpers.py`
  - `src/backend/logistics-data/main.py`
- Requirements:
  - Tracing implementation MUST NOT introduce direct product-path SQL or Azure AI Search dependencies for operational dashboard data.
  - MCP-mediated data contracts MUST remain the source of truth for operational data.

## Contract 6: Obsolete Customization Retirement Safety

- In-scope paths:
  - `src/backend/logistics/monitoring.py`
  - `src/backend/logistics/patches/`
- Requirements:
  - Any preview-era or legacy tracing customization selected for retirement MUST have documented rationale and replacement coverage proof.
  - Required context synchronization behavior MUST remain intact after cleanup.
  - Cleanup MUST include regression validation for trace completeness and AG-UI behavior.

## Validation and Release Gates

- Required checks before release:
  - `uv run --project . poe check`
  - `npm run lint` (if frontend touched)
  - Trace completeness validation against SC-001 through SC-003
- Required evidence artifacts:
  - Trace completeness sample report
  - Failure-path trace validation report (tool and A2A)
  - Compatibility validation notes for AG-UI/CopilotKit flows
