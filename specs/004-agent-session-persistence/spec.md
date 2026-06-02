# Feature Specification: Agent Session Persistence

**Feature Branch**: `[004-agent-session-persistence]`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "create a new specification for agent session / persistence. This spec must uphold the current Agent Framework conversation_id rooted session linkage across Foundry V2 Agent Service, Agent Framework, and CopilotKit. Here are some initial requirements:

- UX in CopilotKit for displaying session history as a vertical list that can fly out from the left hand side.
- Click a previous session loads the user-agent session chat history.
- If possible, the UI components generated from AG-UI tool calls are re-hydrated in the chat window.
- Loading a previous session restores agent context. LLM is able to continue a past conversation based on that context
- Sessions are given an initial user-friendly name in the vertical list.
- Users are able to change the name. Name change flows to backend.
- Users are able to delete items. Deletion flows to backend.
- Solution must extend the current out-of-the-box session persistence in Foundry, which uses a Cosmos DB database connection to persist the session data"

## Clarifications

### Session 2026-06-01

- Q: What should session deletion mean for Foundry-backed persisted history? -> A: Remove the session from the product experience, but allow underlying platform retention or delayed cleanup behind the scenes.
- Q: How much session history should the initial list expose? -> A: Show only the most recent 20 sessions and do not expose older history in this feature.
- Q: How broad should AG-UI artifact restoration be in the first release? -> A: Rehydrate only a defined supported subset in v1, with transcript fallback for all other artifacts.
- Q: How should default session titles be generated? -> A: Use the first meaningful user message, truncated, with a timestamp fallback, and always display session date/time in the history list.
- Q: How should the history list handle sessions that can no longer be restored? -> A: Keep them visible with an unavailable state and block resume.
- Q: How should newly created but zero-turn sessions be handled in history? -> A: Do not show sessions in history until at least one user turn is persisted.
- Q: Should session history be available when running without authentication? -> A: No. In no-auth mode, session history sidebar/features are not available.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Resume Prior Session (Priority: P1)

As a returning user, I can open session history and resume a prior conversation so I can continue work without losing the transcript or the agent's prior context.

**Why this priority**: Conversation continuity is the core value of session persistence and is the primary reason to surface historical sessions in the product.

**Independent Test**: Can be fully tested by completing a conversation, leaving the chat, reopening a prior session from history, and sending a follow-up message that continues the same conversation context.

**Acceptance Scenarios**:

1. **Given** a user has one or more persisted sessions, **When** the user opens the session history flyout, **Then** the system displays up to the 20 most recent sessions as a vertical list ordered by most recent activity and shows a date/time indicator for each entry.
2. **Given** a persisted session in the history list, **When** the user selects that session, **Then** the chat window loads the prior user and agent messages for that session.
3. **Given** a user resumes a prior session, **When** the user sends a new message, **Then** the agent continues the existing conversation rather than starting a disconnected new one.
4. **Given** a user resumes a session that contains previously established agent context, **When** the session finishes loading, **Then** the agent can use that context in its next response.
5. **Given** a session was created but has no persisted user turn yet, **When** history is rendered, **Then** that zero-turn session is not shown in the visible session list.
6. **Given** the app is running in no-auth mode, **When** the user opens chat, **Then** the session history sidebar is not shown and session history actions are unavailable.

---

### User Story 2 - Manage Session List (Priority: P2)

As a user, I can rename or delete saved sessions from the history list so I can keep my chat history organized and understandable.

**Why this priority**: Session persistence becomes hard to use if users cannot identify, rename, or remove sessions after they accumulate.

**Independent Test**: Can be fully tested by creating multiple sessions, renaming one, deleting another, refreshing the application, and confirming the updated history state persists.

**Acceptance Scenarios**:

1. **Given** a newly created session, **When** it first appears in the history list, **Then** it has an initial user-friendly name derived from the first meaningful user message when available, with a timestamp fallback instead of an opaque identifier.
2. **Given** a session in the history list, **When** the user renames it, **Then** the updated name is shown in the list and remains visible after refresh.
3. **Given** a session in the history list, **When** the user deletes it, **Then** it is removed from the list and cannot be reopened from the user interface even if underlying platform cleanup occurs later.
4. **Given** a session rename or delete request, **When** the backend confirms the change, **Then** the frontend reflects the durable updated state without requiring manual reconciliation.

---

### User Story 3 - Restore Rich Chat Artifacts (Priority: P3)

As a user reviewing an earlier conversation, I can see prior tool-generated chat artifacts restored when supported so the reopened session remains useful beyond plain text transcript playback.

**Why this priority**: Rich chat artifacts improve comprehension of past work, but transcript continuity remains more critical than full visual reconstruction.

**Independent Test**: Can be fully tested by reopening a session that previously produced AG-UI tool output and confirming that supported artifacts reappear or fall back gracefully to transcript-only history.

**Acceptance Scenarios**:

1. **Given** a persisted session includes AG-UI tool-generated components that are part of the defined supported restoration subset, **When** the session is reopened, **Then** those components are restored in the chat window in the correct conversation position.
2. **Given** a persisted session includes an AG-UI artifact outside the supported restoration subset or one that otherwise cannot be restored, **When** the session is reopened, **Then** the transcript still loads and the user is informed that the artifact could not be rehydrated.

### Edge Cases

- What happens when the canonical persisted session exists but a user-friendly title is missing? The system must still display the session using a deterministic fallback name based on recent conversation content or creation metadata.
- How does the system handle a previously saved session that is no longer restorable because backing history is unavailable? The system must keep the session visible in the list with an unavailable state, block resume, preserve list integrity, and show a clear unavailable-state message.
- What happens when a rename or delete request conflicts with a change made from another client? The system must show the latest durable state and avoid displaying duplicate or ghost sessions.
- What happens when a user attempts to switch sessions while an agent response is actively streaming? The system must block unsafe switching until the active run is completed or explicitly canceled.
- What happens when rich AG-UI artifacts cannot be rehydrated because required supporting data is no longer available? The transcript must remain available and the missing artifact must degrade gracefully without breaking the rest of the chat view.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide session history in CopilotKit as a left-side flyout containing a vertical list of the authenticated user's persisted sessions.
- **FR-002**: The session history list MUST display up to the 20 most recent sessions in reverse chronological order and show both a user-friendly title and a date/time indicator for each session.
- **FR-003**: The system MUST assign an initial user-friendly title to each new session before the session is first shown in the history list, using the first meaningful user message when available and a timestamp fallback otherwise.
- **FR-004**: Users MUST be able to select a prior session from the history list and load its prior user-agent transcript into the active chat window.
- **FR-005**: Loading a prior session MUST preserve the current conversation-rooted linkage across CopilotKit, Agent Framework, and Foundry Agent Service so that follow-up turns continue within the same canonical persisted session.
- **FR-006**: Loading a prior session MUST restore sufficient prior agent context for the next model response to continue the conversation coherently.
- **FR-007**: The solution MUST extend the existing Foundry-backed session persistence model, including its Cosmos DB-backed storage behavior, rather than replacing it with a disconnected parallel session system.
- **FR-008**: Users MUST be able to rename a session from the history list, and the updated name MUST persist through the backend and be reflected in subsequent session loads.
- **FR-009**: Users MUST be able to delete a session from the history list, and deleted sessions MUST no longer be available for resume from the product experience even if underlying platform retention or delayed cleanup still applies.
- **FR-010**: Rename, delete, and load actions MUST flow through backend service interfaces and produce durable results that remain consistent across refreshes and devices for the same user.
- **FR-011**: The first release MUST define a supported subset of AG-UI tool-generated UI components eligible for restoration during session resume.
- **FR-012**: When a reopened session contains AG-UI tool-generated UI components from that supported subset, the system MUST rehydrate those components in the chat window in their original conversational order.
- **FR-013**: When a prior AG-UI artifact is outside the supported restoration subset or otherwise cannot be rehydrated, the system MUST preserve transcript continuity and clearly indicate that the artifact could not be restored.
- **FR-014**: AG-UI and CopilotKit interaction behavior for new and in-progress conversations MUST remain unchanged except for the addition of history browsing, loading, renaming, and deletion capabilities.
- **FR-015**: The system MUST scope session history, session loading, and session mutations to the authorized user and MUST prevent exposure of another user's sessions or session titles.
- **FR-016**: The system MUST preserve existing operational data access behavior through MCP service interfaces; session persistence changes MUST not alter how operational flight data is sourced.
- **FR-017**: Service-boundary validation contracts MUST verify identifier continuity, history retrieval, mutation behavior, authorization, and supported-artifact restoration behavior across CopilotKit, the backend API, Agent Framework session handling, Foundry Agent Service persistence, and any feature-owned session metadata.
- **FR-018**: The system MUST provide clear user-visible states for loading, unavailable history, partial restoration, rename failure, and delete failure outcomes.
- **FR-019**: If a user attempts to switch sessions while an agent run is active, the system MUST require the active run to finish or be explicitly canceled before switching.
- **FR-020**: If a session remains listed but its backing history can no longer be restored, the system MUST keep the session visible with an unavailable state and MUST block resume attempts for that entry.
- **FR-021**: The frontend MUST persist session history view state and session metadata cache locally in browser localStorage so session list interactions are immediately responsive.
- **FR-022**: On application startup, the frontend MUST hydrate session state from localStorage first, then synchronize with backend session APIs and reconcile differences deterministically.
- **FR-023**: User interactions for session rename and delete MUST apply locally first for responsiveness and MUST then invoke backend APIs for durable thread metadata updates/deletes.
- **FR-024**: If local and backend session states diverge, the system MUST reconcile to backend-authoritative durable state while preserving clear user feedback about pending, synced, or failed operations.
- **FR-025**: The session history list MUST exclude zero-turn conversations and only include sessions with at least one persisted user turn (a Foundry conversation item with `type=message` and `role=user` retrievable through supported Conversations APIs).
- **FR-026**: When authentication is disabled (no-auth mode), the session history sidebar and session history actions (list/load/rename/delete) MUST be unavailable in the frontend.

### Key Entities *(include if feature involves data)*

- **Session Summary**: The user-visible representation of a persisted conversation in the history list, including title, displayed date/time, recency ordering, and availability state.
- **Canonical Session Linkage**: The persisted relationship that keeps the CopilotKit conversation identifier, Agent Framework session identifier, and Foundry conversation record aligned for continuation.
- **Session Transcript**: The ordered set of prior user messages, agent responses, and visible tool outputs associated with a resumable conversation.
- **Session Artifact**: A non-text chat element produced by a prior interaction, including tool-generated UI components that may be restorable during session reload.
- **Session Mutation**: A user-initiated change to session metadata or availability, such as rename or delete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In usability testing, at least 95% of users can locate and reopen a prior session from the 20-entry history list in under 15 seconds without assistance.
- **SC-002**: In validation testing, 100% of resumed sessions continue under the same canonical conversation linkage rather than creating a disconnected follow-up conversation.
- **SC-003**: At least 95% of successful session load attempts restore the full prior transcript and allow the user to continue the conversation on the first follow-up turn.
- **SC-004**: At least 95% of successful rename and delete actions are reflected in the user-visible history list within 5 seconds and remain correct after refresh.
- **SC-005**: At least 90% of sessions containing artifacts from the defined supported AG-UI restoration subset restore those artifacts successfully, and 100% of artifacts outside that subset degrade without blocking transcript access.
- **SC-006**: Authorization and privacy validation shows zero cases where one user can view, rename, delete, or resume another user's session.
- **SC-007**: 100% of sessions shown in the 20-entry history list receive an initial user-friendly title before first display and show a date/time indicator in the list.
- **SC-008**: 100% of unrecoverable sessions that remain in the visible history list are marked unavailable and do not allow resume attempts.
- **SC-009**: At least 95% of session history open, rename, and delete interactions render immediate local UI feedback within 100 ms before backend round-trip completion.
- **SC-010**: At least 99% of local-to-backend sync operations converge to backend-authoritative state within 10 seconds of app startup or mutation dispatch under normal network conditions.
- **SC-011**: 100% of zero-turn conversations are excluded from visible session history in validation scenarios covering fresh page load and immediate switch-to-history behavior.
- **SC-012**: 100% of no-auth mode validation runs show no session history sidebar/actions and no session history API calls initiated from the UI.

## Assumptions

- Existing authentication and user scoping mechanisms remain the basis for determining which sessions a user can view and mutate.
- Foundry persistence remains the canonical source of conversation history, and this feature may add only the metadata or restoration information needed to make that persistence usable in the product experience.
- Session history in this feature covers CopilotKit chat sessions for the current product and does not introduce cross-application history sharing.
- The first release exposes only the 20 most recent sessions per user and does not include access to older history.
- The first release rehydrates only a defined supported subset of AG-UI artifacts and uses transcript-safe fallback behavior for all other artifact types.
- Default session naming uses the first meaningful user message when available, and the history list always displays date/time metadata for each session entry.
- When exact restoration of a prior AG-UI artifact is not possible, preserving transcript continuity is the higher priority outcome.
- Unrecoverable sessions may remain visible in the history list for user awareness, but they are non-resumable and clearly marked unavailable.
- Session deletion hides the session from the product experience immediately, while underlying Foundry or platform retention rules may remove the backing record later.
- The flyout session history experience will remain usable across supported desktop and responsive layouts without requiring a separate mobile-only workflow.
- Browser localStorage is available for supported clients and session cache keys can be scoped to authenticated user context.
- Conversation creation may occur before the first user turn; those zero-turn sessions are intentionally hidden from session history until a user message is persisted.
- No-auth mode is treated as a chat-only experience and does not expose session history features.
