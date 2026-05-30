# Research: Full Foundry V2 Tracing

## Decision 1: Keep app-owned AG-UI runtime and instrument end-to-end spans

- Decision: Keep the current app-owned AG-UI path (CopilotKit proxy to backend `/logistics`) and implement full trace correlation across conversation turn, tool calls, and A2A interactions rather than switching immediately to a fully hosted-agent-only runtime.
- Rationale: This repository currently orchestrates tools through backend-owned Agent Framework code and AG-UI event streaming. Preserving this architecture minimizes behavior risk while still meeting trace visibility requirements.
- Alternatives considered:
  - Immediate full migration to hosted-agent-only orchestration: rejected for this feature due scope and regression risk to tool orchestration and AG-UI behavior.
  - No additional correlation design beyond existing OpenTelemetry: rejected because current trace views lack guaranteed turn/tool/A2A linkage.
- Sources:
  - MAF skill: `.github/skills/microsoft-agent-framework/SKILL.md`, `.github/skills/microsoft-agent-framework/references/python.md`
  - Repo context: `src/backend/api/main.py`, `src/frontend/src/app/api/copilotkit/[[...path]]/route.ts`
  - CopilotKit/AG-UI docs MCP: `mcp_copilotkit_mc_search-ag-ui-docs`

## Decision 2: Use Foundry-native and Azure Monitor instrumentation with explicit GenAI tracing gates

- Decision: Standardize on currently supported Foundry-native and OpenTelemetry instrumentation paths with Azure Monitor/Application Insights, including explicit environment-gated GenAI tracing configuration.
- Rationale: Runtime evidence in this repo showed GenAI tracing can be disabled by default unless required environment gating is enabled. This directly impacts whether model and tool-level spans appear as expected.
- Alternatives considered:
  - Rely only on generic FastAPI/request tracing: rejected because it does not guarantee GenAI-level spans and tool-call semantic depth.
  - Retain mixed legacy/preview instrumentation variants without consolidation: rejected because it increases confusion and duplicate/low-signal telemetry.
- Sources:
  - Microsoft Learn: Agent Framework observability guidance
  - Microsoft Learn: Foundry tracing article for OpenAI SDK + Application Insights linkage
  - Runtime evidence from local startup warning and installed SDK telemetry gate behavior (`azure.ai.projects.telemetry`)
  - Azure best-practices MCP: `mcp_azure_mcp_get_azure_bestpractices` (`get_azure_bestpractices_ai_app`)

## Decision 3: Model trace correlation around AG-UI identifiers and tool call identifiers

- Decision: Use conversation/thread identity, run identity, and tool call identity as first-class correlation keys across frontend, backend, tool execution, and A2A interactions.
- Rationale: AG-UI protocol defines run/thread/tool-call lifecycle events and identifiers; aligning trace contracts to these identifiers gives deterministic per-turn and per-tool linking.
- Alternatives considered:
  - Correlate only by timestamp windows: rejected due ambiguity under concurrency.
  - Correlate only by conversation id: rejected because it is insufficient for per-turn and per-tool diagnostics.
- Sources:
  - AG-UI docs MCP: lifecycle and tool call event guidance (`RUN_*`, `TOOL_CALL_*`)
  - AG-UI code MCP: generated event types showing `toolCallId` and lifecycle event structures (`events.ts`)

## Decision 4: Instrument A2A interactions as child spans of the originating turn

- Decision: Capture A2A request/response/failure as explicit spans linked to the originating conversation turn trace and emit stable attributes for source agent, target agent, and outcome.
- Rationale: A2A interactions are a required user story outcome and currently can be opaque without explicit instrumentation and correlation keys.
- Alternatives considered:
  - Treat A2A activity only as logs: rejected because logs alone do not provide reliable timeline and parent-child span relationships.
  - Isolate A2A traces from turn traces: rejected because it breaks debugging flow requested by spec.
- Sources:
  - Spec requirements FR-004, FR-005, FR-006, FR-007
  - Existing A2A architecture in `src/backend/api/agents/tools/recommendation_tools.py` and `src/backend/agent-a2a`

## Decision 5: Use cadence backend as a reference for stable telemetry naming and selective FoundryAgent usage

- Decision: Reuse proven cadence patterns where applicable:
  - stable agent naming for `gen_ai.agent.*` attributes
  - explicit manual spans for critical tool execution paths
  - selective use of FoundryAgent where hosted agent references improve portal correlation
- Rationale: Cadence demonstrates practical hybrid usage (`FoundryChatClient` + `FoundryAgent`) and explicit span attributes while keeping runtime behavior predictable.
- Alternatives considered:
  - Blindly copy cadence architecture: rejected because this repo has different domain flows and AG-UI constraints.
  - Ignore cadence lessons: rejected because user explicitly requested cadence as reference and it contains relevant tracing improvements.
- Sources:
  - `travisnielsen/cadence` backend excerpts (`src/backend/workflow/clients.py`, `src/backend/config/settings.py`, `src/backend/api/monitoring.py`)

## Decision 6: Identify and retire obsolete preview-era tracing customizations

- Decision: During implementation, inventory current tracing and patch customizations and retire those no longer needed under current supported SDK behavior, while preserving required AG-UI context synchronization behavior.
- Rationale: The repository contains patch infrastructure and prior workaround notes; some may now be obsolete and can add noise or complexity.
- Alternatives considered:
  - Keep all historical tracing customizations indefinitely: rejected due maintenance cost and signal quality impact.
  - Remove all customizations at once: rejected because some AG-UI context behavior is still required.
- Sources:
  - Local code: `src/backend/api/patches/*`, `src/backend/api/monitoring.py`
  - Prior upgrade notes and runtime analysis context

## Implementation Notes for Foundry V2 Traceability

- Preserve frontend behavior and route shape while strengthening correlation fields and span relationships.
- Validate App Insights linkage and Foundry project tracing visibility as a required acceptance path.
- Add explicit validation scenarios for turn completeness, tool completeness, and A2A completeness against SC-001 to SC-003.
- Treat telemetry duplication and sensitive-data exposure as explicit design concerns; default to least-privilege data capture outside controlled debugging contexts.

## Source Provenance Appendix (Phase 6)

- Microsoft Learn: Agent Framework overview and observability guidance.
- Microsoft Learn: Azure AI Foundry/OpenAI tracing guidance for Application Insights.
- CopilotKit and AG-UI documentation via MCP semantic search tools.
- Cadence reference repository (`travisnielsen/cadence`) for telemetry naming and hybrid instrumentation patterns.
