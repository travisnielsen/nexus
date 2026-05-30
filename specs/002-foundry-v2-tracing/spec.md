# Feature Specification: Full Foundry V2 Tracing

**Feature Branch**: `002-foundry-v2-tracing`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "create a new feature spec for adding full, end-to-end tracing in the Microsoft Foundry V2 portal. Tracing must capture details for all tool calls and A2A interactinos for each conversation turn. We will be using Appliction Inights + Foundry V2 native SDKs using current supported techniques. Use this repo as an example: travisnielsen/cadence"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Complete Turn Traces (Priority: P1)

As an engineer monitoring production conversations, I can open a conversation in the Foundry V2 portal and see a complete trace for every turn, including model work and all tool activity, so I can diagnose behavior without switching across multiple systems.

**Why this priority**: End-to-end turn visibility is the core value of the feature and the prerequisite for all operational debugging.

**Independent Test**: Can be fully tested by running a multi-turn conversation that triggers several tool calls and confirming each turn appears in the portal with correlated trace details.

**Acceptance Scenarios**:

1. **Given** a conversation with multiple user turns, **When** an operator opens tracing for that conversation, **Then** each turn is listed with a trace that can be inspected end-to-end.
2. **Given** a turn that triggers one or more tool calls, **When** the turn trace is expanded, **Then** all tool calls for that turn are visible and attributable to that turn.

---

### User Story 2 - Trace A2A Interactions Per Turn (Priority: P2)

As an engineer investigating multi-agent behavior, I can see all A2A interactions associated with each conversation turn, so I can understand handoffs and downstream dependencies.

**Why this priority**: A2A observability is required to trust recommendation quality and diagnose failures beyond local tool execution.

**Independent Test**: Can be fully tested by running a turn that invokes A2A interactions and verifying those interactions appear in the same turn-level trace context.

**Acceptance Scenarios**:

1. **Given** a turn that causes one or more A2A interactions, **When** trace details are viewed, **Then** each A2A interaction is visible with enough metadata to identify source, destination, and outcome.
2. **Given** an A2A interaction fails or times out, **When** trace details are viewed, **Then** the failure state and affected turn are clearly visible.

---

### User Story 3 - Audit and Operate with Consistent Trace Coverage (Priority: P3)

As a platform owner, I can confirm trace coverage and quality for active conversations over time, so I can satisfy operational review and incident response needs.

**Why this priority**: Governance and operational readiness depend on consistent trace completeness, but this is secondary to delivering turn-level visibility first.

**Independent Test**: Can be fully tested by reviewing recent conversations over a defined window and verifying trace completeness and correlation consistency against expected activity.

**Acceptance Scenarios**:

1. **Given** recent production conversations, **When** coverage is reviewed, **Then** turn traces are consistently present for completed turns.
2. **Given** trace data from the same conversation in different monitoring views, **When** records are compared, **Then** they can be correlated without ambiguity.

### Edge Cases

- What happens when a turn has zero tool calls and zero A2A interactions?
- How does the system handle partial trace delivery when one downstream telemetry sink is temporarily unavailable?
- How does the system handle duplicate or retried tool and A2A operations within the same turn?
- What happens when long-running turns exceed normal completion windows?
- How are concurrent turns from different conversations prevented from being mis-correlated?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce a trace record for every completed conversation turn that is visible in the Microsoft Foundry V2 portal.
- **FR-002**: The system MUST associate each turn trace with a stable conversation identifier and turn identifier.
- **FR-003**: The system MUST capture all tool calls initiated during a turn and link them to the originating turn trace.
- **FR-004**: The system MUST capture all A2A interactions initiated during a turn and link them to the originating turn trace.
- **FR-005**: The system MUST record start time, end time, and outcome status for each turn, tool call, and A2A interaction.
- **FR-006**: The system MUST preserve trace correlation across frontend request flow, backend orchestration flow, tool execution flow, and A2A flow for the same turn.
- **FR-007**: The system MUST expose enough trace context to identify failed tool calls and failed A2A interactions without requiring source code inspection.
- **FR-008**: The system MUST support trace discovery for recent conversations within an operational review window of at least 24 hours.
- **FR-009**: Operational flight data access paths MUST continue to use MCP service interfaces; tracing changes MUST NOT bypass MCP data contracts.
- **FR-010**: AG-UI and CopilotKit interaction behavior MUST remain functionally equivalent for end users after tracing enhancements.
- **FR-011**: Service boundary validation contracts for trace identity fields (conversation, turn, tool call, A2A interaction) MUST be defined and enforced at boundaries where traces are emitted or forwarded.
- **FR-012**: The solution MUST use currently supported Microsoft Foundry V2 native SDK tracing techniques and Application Insights integration patterns available at implementation time.
- **FR-013**: The system MUST provide a documented method to verify trace completeness for a sampled set of conversations.

### Key Entities *(include if feature involves data)*

- **Conversation Trace**: Represents all trace data for one conversation; includes conversation identifier, time window, and collection of turn traces.
- **Turn Trace**: Represents one conversational turn; includes turn identifier, actor, timing, status, and links to tool calls and A2A interactions.
- **Tool Call Trace**: Represents one tool invocation within a turn; includes tool identity, invocation timing, outcome, and correlation keys.
- **A2A Interaction Trace**: Represents one agent-to-agent interaction within a turn; includes source agent, target agent, timing, outcome, and correlation keys.
- **Trace Correlation Context**: Represents shared identifiers used to correlate frontend, backend, tool, and A2A activity for the same turn.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 99% of completed conversation turns in a 7-day observation period have a corresponding trace visible in the Foundry V2 portal.
- **SC-002**: At least 99% of traced turns that execute tools show all tool calls linked to the correct turn.
- **SC-003**: At least 99% of traced turns that execute A2A interactions show all A2A interactions linked to the correct turn.
- **SC-004**: During validation drills, engineers can identify the failing step (turn, tool call, or A2A interaction) for traced failed conversations within 5 minutes in at least 90% of cases.
- **SC-005**: Post-release, no increase greater than 5% is observed in user-visible conversation failure rate attributable to tracing changes.

## Assumptions

- Existing Foundry project resources and Application Insights resources remain available and authorized for this application.
- Existing conversation and session identity concepts remain stable and can be reused for trace correlation.
- Current user-facing chat behavior and data workflows are preserved; this feature focuses on observability and correlation quality.
- Operational teams have access to the Foundry V2 portal and required monitoring permissions for trace review.
- The cadence repository is used as a reference implementation pattern, but this feature is scoped to this repository's architecture and constraints.
