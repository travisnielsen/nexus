# Research: Agent Session Persistence

## Decision 1: Keep Foundry conversation ID as the single canonical session key across all layers

- Decision: Use the existing Foundry `conversation.id` (`conv_*`) as the canonical key for session resume, with CopilotKit `threadId` and Agent Framework `service_session_id` remaining direct aliases.
- Rationale: This preserves the current architecture (`POST /api/conversations` -> frontend `threadId` -> `use_service_session=True`) and avoids split-brain session state.
- Alternatives considered:
  - Introduce a parallel app-generated session ID and map to Foundry conversation IDs: rejected due continuity risk and extra reconciliation complexity.
  - Store complete transcript only in app-owned persistence and treat Foundry as secondary: rejected because requirements explicitly mandate extending Foundry persistence, not replacing it.
- Sources:
  - MAF skill: `.github/skills/microsoft-agent-framework/SKILL.md`
  - MAF Python reference: `.github/skills/microsoft-agent-framework/references/python.md`
  - Repo context: `src/backend/logistics/main.py`, `src/backend/logistics/agents/logistics_agent.py`, `src/frontend/src/components/NoAuthCopilotKit.tsx`, `src/frontend/src/components/AuthenticatedCopilotKit.tsx`
  - Microsoft Learn: Agent Framework overview (`learn.microsoft.com/agent-framework/overview/agent-framework-overview`)

## Decision 2: Add a feature-owned metadata envelope while keeping Foundry transcript persistence as source of truth

- Decision: Persist user-facing session metadata (title, soft-delete visibility, availability state, artifact restoration manifest, updated timestamps) in Azure Cosmos DB as a feature-owned metadata store, while transcript/context remains Foundry-native.
- Rationale: Foundry conversation persistence provides durable conversation state, while product UX needs extra metadata not guaranteed to exist in service-managed transcript records. The metadata store must align with deployment constraints by using Cosmos DB in a private VNET path that is not directly reachable from frontend clients.
- Access boundary: Cosmos DB access for session metadata is restricted to the Logistics API service path only. Frontend and chat clients interact through backend session endpoints; they never access Cosmos DB directly.
- Alternatives considered:
  - Derive everything from transcript at read time: rejected because rename/delete/unavailable state require explicit durable flags and conflict handling.
  - Hard-delete Foundry conversation on user delete: rejected because clarified requirement is product-level removal with possible delayed platform retention/cleanup.
  - Expose Cosmos DB directly to the frontend over public endpoints: rejected due security and network-boundary requirements.
- Sources:
  - Feature spec clarifications and FR-007/FR-009/FR-010/FR-020
  - Repo architecture docs: `.github/copilot-instructions.md`
  - Azure AI app best practices MCP: `mcp_azure_mcp_get_azure_bestpractices` (`get_azure_bestpractices_ai_app`)
  - Microsoft Foundry docs hub (`learn.microsoft.com/azure/foundry/`)

## Decision 3: Implement bounded AG-UI artifact rehydration using explicit supported-type contracts

- Decision: Define a v1 supported subset for AG-UI artifact restoration and persist a normalized restoration descriptor per restorable artifact; all unsupported artifacts degrade to transcript-only rendering with explicit user messaging.
- Rationale: Requirements prioritize transcript continuity over perfect reconstruction and explicitly allow a supported subset with fallback.
- Alternatives considered:
  - Attempt full generic replay of all historical AG-UI events: rejected for v1 due event-shape drift risk and high complexity.
  - Skip artifact restoration entirely: rejected because FR-011 and FR-012 require supported restoration behavior.
- Sources:
  - AG-UI docs via CopilotKit MCP tools: serialization, messages, interrupts (`mcp_copilotkit_mc_search-ag-ui-docs`, `mcp_copilotkit_mc_explore-docs`)
  - AG-UI code evidence: event and tool-call lifecycle snippets (`mcp_copilotkit_mc_search-ag-ui-code`)

## Decision 4: Expose explicit session APIs for list/load/rename/delete with optimistic UI + backend-confirmed durability

- Decision: Add backend endpoints for `list`, `load`, `rename`, and `delete` session operations and proxy them through frontend app routes. Frontend applies local-first state updates (localStorage + in-memory state) for immediate interaction responsiveness and then synchronizes/reconciles to backend-confirmed durable state.
- Rationale: The spec requires durable backend-mediated mutations and cross-device consistency.
- Alternatives considered:
  - Frontend-only local mutation state: rejected because not durable and breaks cross-device consistency.
  - Overloading CopilotKit thread endpoint (`/api/copilotkit/threads`) as mutation API: rejected because current route intentionally returns empty threads and is not the right mutation boundary.
- Sources:
  - Repo context: `src/frontend/src/app/api/copilotkit/[[...path]]/route.ts`, `src/frontend/src/app/api/conversations/route.ts`
  - Feature requirements FR-002, FR-004, FR-008, FR-009, FR-010

## Decision 9: Use localStorage-first session UX with startup synchronization

- Decision: Persist session history cache locally in browser localStorage (user-scoped keyspace) and hydrate it first on startup; then run background synchronization against backend list/load endpoints and reconcile to backend-authoritative state.
- Rationale: Local-first interactions provide fast UI responsiveness while preserving backend durability, authorization, and cross-device consistency.
- Alternatives considered:
  - Backend-only interaction with no local cache: rejected for perceived latency and lower responsiveness.
  - Local-only persistence with no backend reconciliation: rejected because it breaks cross-device consistency and durable mutations.
- Reconciliation policy: Rename/delete/apply-load interactions are reflected locally immediately with pending sync status, then upgraded to synced or reverted with user-visible failure state based on API result.
- Sources:
  - Feature implementation refinement requirement
  - Session persistence API contract in `specs/004-agent-session-persistence/contracts/session-persistence-api-contract.md`

## Decision 10: Use Foundry Conversations API as the transcript retrieval contract

- Decision: Session reload MUST retrieve transcript/history via supported Foundry Conversations operations (for example `openai_client.conversations.items.list(conversation_id)`), then normalize those items into the backend session load payload for CopilotKit hydration.
- Rationale: Microsoft SDK samples and tests show an explicit, supported conversation-items read path for reconstructing multi-turn state, including tool call artifacts and function outputs.
- Scope boundary: Raw Cosmos document parsing for transcript reconstruction is out of scope for this feature.
- Alternatives considered:
  - Parse raw Cosmos containers directly as the primary contract: rejected because internal storage shape is not a stable, publicly versioned schema contract for app logic.
  - Rely only on response continuation without transcript hydration: rejected because UI replay requirements need explicit transcript payloads.
- Sources:
  - Azure SDK Python sample: `sdk/ai/azure-ai-projects/samples/agents/sample_agent_basic.py` (conversation creation, item creation)
  - Azure SDK Python test evidence: `sdk/ai/azure-ai-projects/tests/agents/tools/test_agent_tools_with_conversations.py` (`openai_client.conversations.items.list(conversation.id)`)
  - Microsoft Learn quickstart: `learn.microsoft.com/azure/foundry/quickstarts/get-started-code`
  - Microsoft Learn SDK overview: `learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview`

## Decision 5: Enforce session switching safety and unavailable-state behavior at both UI and API layers

- Decision: Block session switching while a run is active unless canceled/completed, and represent unrecoverable sessions as visible-but-unavailable entries with blocked resume.
- Rationale: Edge-case requirements require deterministic user protection and clear state messaging.
- Alternatives considered:
  - Allow immediate switch during active streaming: rejected due race conditions and known "thread already running" behavior.
  - Hide unavailable sessions entirely: rejected because requirement calls for visible unavailable entries.
- Sources:
  - Feature spec edge cases and FR-018/FR-019/FR-020
  - Existing known issue note in `.github/copilot-instructions.md` (thread already running limitation)

## Decision 6: Preserve constitution constraints and current MCP operational data path

- Decision: Session persistence feature touches chat/session boundaries only and must not modify MCP operational dashboard data sourcing.
- Rationale: Constitution Principle I is non-negotiable for operational data paths.
- Alternatives considered:
  - Co-locate session metadata in MCP operational data contracts: rejected because session metadata is not operational flight data and should remain separate from MCP source-of-truth data domain.
- Sources:
  - Constitution: `.specify/memory/constitution.md`
  - Existing MCP pattern docs: `.github/copilot-instructions.md`

## Decision 7: Enforce private-network data access for session persistence metadata

- Decision: Session metadata storage uses Cosmos DB in a private VNET topology and is reachable only by Logistics API backend identity and network path.
- Rationale: Session metadata includes user-scoped conversation descriptors and must be protected by network isolation in addition to authorization checks.
- Alternatives considered:
  - Public Cosmos endpoint with credential-only controls: rejected because network isolation is an explicit platform requirement.
  - Shared direct access path from frontend to Cosmos DB: rejected because all persistence mutations and retrievals must be backend-mediated.
- Sources:
  - Feature request constraint from implementation refinement
  - Repo private-networking baseline: `specs/003-private-networking/plan.md`
  - Session persistence API contract in `specs/004-agent-session-persistence/contracts/session-persistence-api-contract.md`

## Decision 8: Use idempotent Cosmos metadata bootstrap (create-if-not-exists)

- Decision: The Logistics API owns session metadata schema bootstrap and must execute idempotent create-if-not-exists logic for Cosmos DB resources required by this feature (database/container and indexes/partition policy if absent).
- Rationale: Session persistence rollout must be safe across environments where metadata resources may not yet exist, while avoiding duplicate creation or destructive reconfiguration in existing environments.
- Alternatives considered:
  - Manual one-time portal provisioning only: rejected because it increases drift risk and weakens deployment repeatability.
  - Fail startup when resources are missing: rejected because it creates avoidable operational outages during first deployment.
- Sources:
  - Feature implementation refinement requirement
  - Session persistence API contract in `specs/004-agent-session-persistence/contracts/session-persistence-api-contract.md`

## Research Source Validation

- MAF-related findings were grounded in `.github/skills/microsoft-agent-framework/SKILL.md` and `.github/skills/microsoft-agent-framework/references/python.md`.
- CopilotKit/AG-UI findings include MCP exploration evidence from:
  - `mcp_copilotkit_mc_search-ag-ui-docs`
  - `mcp_copilotkit_mc_search-ag-ui-code`
  - `mcp_copilotkit_mc_explore-docs`
- Azure/Microsoft platform findings are backed by:
  - `mcp_azure_mcp_get_azure_bestpractices` (`get_azure_bestpractices_ai_app`)
  - Microsoft Learn first-party pages fetched for Agent Framework and Foundry docs.

Note: The mode requested `mcp_azure_mcp_documentation`; this specific tool is not available in the current toolchain, so Microsoft Learn first-party pages were fetched directly as the nearest equivalent evidence source.
