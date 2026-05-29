# Contract: Foundry Client Configuration and Compatibility Mapping

Created: 2026-05-29

## Goal

Define environment and runtime contract for Foundry-native chat client migration.

## Environment Variable Contract

| Variable | Purpose |
|---|---|
| FOUNDRY_PROJECT_ENDPOINT | Foundry project endpoint for the chat client |
| FOUNDRY_MODEL | Foundry deployment name / model identifier |

## Client Contract

- Client factory MUST return `SupportsChatGetResponse`.
- Default implementation MUST use `agent_framework.foundry.FoundryChatClient`.
- Credential path remains async and non-blocking (`azure.identity.aio` supported).

## Compatibility Requirements

- Existing `create_logistics_agent(chat_client)` integration contract is unchanged.
- Tool registration and execution semantics remain unchanged from caller perspective.
- Thread/session behavior remains compatible with existing AG-UI service-session usage.

## Version and Source Verification

- Verify selected Agent Framework Foundry package/client APIs are latest supported using:
  - Microsoft Learn (`mcp_azure_mcp_documentation`)
  - Agent Framework skill guidance
  - SDK/repository source verification when needed
