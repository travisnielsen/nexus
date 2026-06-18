# Research: User Feedback Storage

## Decision 1: Keep one backend feedback service boundary for both feedback kinds
- Decision: Use a single backend submission boundary (`POST /logistics/feedback`) for turn feedback and overall-experience feedback, differentiated by `feedback_kind`.
- Rationale: This preserves existing integration points, keeps telemetry and persistence behavior consistent, and reduces split-path drift between immediate thumbs and AG-UI-invoked overall cards.
- Alternatives considered:
- Separate endpoints for each kind. Rejected because it duplicates validation, idempotency, and telemetry logic.
- Frontend direct persistence for one flow and backend for another. Rejected because it breaks contract consistency and observability guarantees.
- Sources:
- Repo evidence from existing endpoint and TODO persistence path in `src/backend/logistics/main.py`.
- CopilotKit/AG-UI docs exploration: `/ag-ui-docs/concepts/tools.mdx` (tool-call lifecycle and frontend-defined tool behavior).

## Decision 2: Durable storage success is acceptance boundary; telemetry is decoupled with explicit failure state
- Decision: Accept submissions when Cosmos persistence succeeds; emit telemetry as best-effort with explicit operational status and retry path.
- Rationale: Matches clarified requirement and prevents user-facing failures caused by transient telemetry pipeline issues.
- Alternatives considered:
- Require both storage and telemetry to succeed. Rejected because it increases user-visible failure without improving data durability.
- Fire-and-forget without status tracking. Rejected because operators cannot distinguish partial failure states.
- Sources:
- Clarification outcomes in `spec.md`.
- Microsoft Learn guidance on correlation and custom telemetry data model (operation-level correlation, custom events):
- https://learn.microsoft.com/azure/azure-monitor/app/api-custom-events-metrics

## Decision 3: Use canonical `conv_*` session identity and feedback-kind-specific correlation fields
- Decision: Persist canonical `conversation_id` (`conv_*`) for all feedback records; require `turn_id` and `trace_id` for turn feedback; allow optional `card_turn_id` association for overall feedback.
- Rationale: Keeps compatibility with existing session continuity architecture while preserving kind-specific correlation precision.
- Alternatives considered:
- Introduce a separate feedback session key. Rejected because it conflicts with existing session continuity behavior.
- Make turn correlation optional for turn feedback. Rejected because it weakens analytics and traceability.
- Sources:
- Existing architecture guidance in `.github/copilot-instructions.md`.
- Existing session persistence conventions in backend session services.

## Decision 4: Idempotency model is latest-write-wins with deterministic logical keys
- Decision: Use upsert semantics with one effective feedback record per logical target and user.
- Rationale: This satisfies repeat-submission behavior and comment-after-vote updates without creating duplicate analytics artifacts.
- Alternatives considered:
- Append-only submission log as source of truth. Rejected for first release because retrieval and analytics become ambiguous for effective feedback state.
- Client-generated idempotency only. Rejected because cross-client reliability and replay handling are weaker.
- Sources:
- Clarified requirements in `spec.md`.
- Existing Cosmos upsert pattern in `src/backend/logistics/services/session_service.py`.

## Decision 5: Overall experience feedback must be AG-UI tool-call initiated, not bypass chat flow
- Decision: Trigger overall feedback through CopilotKit and AG-UI conversational/tool-call flow, then submit resulting card data to the same backend feedback endpoint.
- Rationale: Preserves interaction integrity and keeps chat state/session continuity aligned with existing framework behavior.
- Alternatives considered:
- Render overall card through a non-chat side channel. Rejected because it bypasses AG-UI/CopilotKit interaction contracts.
- Treat overall feedback as just another turn vote. Rejected because the feature requires distinct feedback kind semantics.
- Sources:
- AG-UI tools concept docs (`/ag-ui-docs/concepts/tools.mdx`) from CopilotKit MCP docs exploration.
- Repo chat integration patterns in `src/frontend/src/app/page.tsx` and agent tool registration in `src/backend/logistics/agents/logistics_agent.py`.

## Decision 6: Follow Microsoft Agent Framework patterns for async, typed contracts, and observability
- Decision: Implement new feedback tool/service code using async methods, typed Pydantic contracts, and explicit telemetry instrumentation consistent with existing MAF-aligned service architecture.
- Rationale: Aligns with repository conventions and constitutional requirements for typed boundaries and observability.
- Alternatives considered:
- Synchronous helper path in endpoint only. Rejected because it does not fit established async service composition.
- Unstructured dict payloads across boundary. Rejected due to contract drift risk.
- Sources:
- MAF skill guidance: `.github/skills/microsoft-agent-framework/SKILL.md`.
- Microsoft Learn MAF overview:
- https://learn.microsoft.com/agent-framework/overview/agent-framework-overview

## Source Validation Checklist
- MAF-related findings reference `.github/skills/microsoft-agent-framework/SKILL.md`: Yes.
- CopilotKit/AG-UI findings include MCP docs exploration evidence: Yes (`/ag-ui-docs/concepts/tools.mdx`).
- Azure/Microsoft platform findings backed by Microsoft Learn sources: Yes (MAF overview and Azure Monitor custom events/correlation docs).
