# Contract: Upgrade Compatibility and Boundary Guarantees

## Purpose

Define the externally visible behavior and boundary contracts that MUST remain compatible during repository dependency upgrades.

## Contract 1: Backend Agent Client Factory

- In-scope files:
  - `src/backend/api/clients.py`
  - `src/backend/api/agents/logistics_agent.py`
- Requirements:
  - The factory MUST return a `SupportsChatGetResponse` compatible client.
  - Default implementation MUST be Foundry-native (`FoundryChatClient`).
  - Client implementation MUST remain async credential compatible.
  - Existing agent construction path (`create_logistics_agent`) MUST require no behavior change to tool registration semantics.
- Compatibility guarantee:
  - No change to public REST endpoint contracts solely due to chat-client migration.

## Contract 2: AG-UI/CopilotKit Streaming Behavior

- In-scope files:
  - `src/backend/api/main.py`
  - `src/backend/api/patches/agui_event_stream.py`
  - `src/frontend/src/app/api/copilotkit/route.ts`
- Requirements:
  - AG-UI lifecycle/tool/state events MUST remain protocol-compatible.
  - Tool call streaming semantics (`TOOL_CALL_*` progression) MUST remain intact.
  - Thread/session continuity MUST remain compatible with `use_service_session=True` behavior.
- Compatibility guarantee:
  - No regression in existing dashboard/chat interaction flows caused by transport/protocol changes.

## Contract 3: MCP-mediated Data Path Integrity

- In-scope files:
  - `src/backend/api/agents/utils/mcp_client.py`
  - `src/backend/api/agents/utils/data_helpers.py`
  - `src/backend/mcp/main.py`
- Requirements:
  - Feature MUST NOT introduce direct product-path SQL/Azure AI Search access bypassing MCP service interfaces.
  - Existing MCP REST and tool/resource access patterns MUST remain operational.
- Compatibility guarantee:
  - Operational data retrieval for flight/dashboard paths remains MCP-mediated.

## Contract 4: Validation and Release Gate Contract

- Requirements:
  - Python scopes run monorepo quality checks (`uv run --project . poe check`).
  - Frontend scopes run lint and build validation (`npm run lint`, `npm run build` in touched projects).
  - Critical regression scenarios MUST be 100% pass before release.
- Evidence outputs:
  - Dependency change summary, lockfile update records, and validation results captured in release notes/artifact docs.
