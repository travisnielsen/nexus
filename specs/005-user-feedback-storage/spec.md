# Feature Specification: User Feedback Storage

**Feature Branch**: `[005-user-feedback-storage]`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "Define a unified, durable, and analytics-friendly pattern for capturing user feedback (like, dislike, optional comment) on agent responses generated through Microsoft Foundry, Agent Framework, and CopilotKit. Feedback must be associated with the Foundry conversation session (`conv_*`), the agent turn, and the Application Insights trace; sent from the UI to a backend endpoint; persisted durably; emitted as correlated telemetry; and remain queryable for analytics and future evaluation workflows."

## Clarifications

### Session 2026-06-17

- Q: Which rule should apply if the same user submits feedback again on the same agent response? -> A: Keep one feedback record per user per response, with the latest submission replacing the earlier one.
- Q: What should happen if durable storage succeeds but telemetry emission fails for a feedback submission? -> A: Accept feedback if durable storage succeeds; emit telemetry separately and mark or retry telemetry failures.
- Q: Should feedback capture be available when the product is running without authentication? -> A: Allow feedback only in authenticated mode; no-auth mode does not show feedback controls.
- Q: Who should be allowed to query stored feedback records in the first release? -> A: Only authorized backend or admin analytics consumers can query feedback records.
- Q: How should optional free-text comments be handled before storage in the first release? -> A: Store comments as submitted, with no special redaction or moderation beyond general payload validity checks, because this is a demo or reference design intended for specific enterprise settings.
- Q: How should overall experience feedback relate to turns when it is submitted through an in-chat feedback card? -> A: It remains a distinct overall-feedback kind, but it can still be associated with the turn represented by the feedback card even though it is not evaluating a specific assistant response.
- Q: How should the overall-feedback card flow be invoked and transported through the chat experience? -> A: The overall-feedback affordance sends an in-chat request to give feedback and the card flow follows the existing CopilotKit and AG-UI tool-call pattern used by the Microsoft Agent Framework integration, even though the submitted feedback record remains a distinct feedback kind.
- Q: Should exact feedback field matrices and idempotency key composition be finalized during clarification? -> A: No. Keep high-level requirements in the spec and defer exact field-level and key-shape specifics to planning contracts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capture Response Feedback (Priority: P1)

As a user reviewing an agent response, I can mark the response as helpful or unhelpful so the product captures immediate quality feedback tied to the exact conversation turn.

**Why this priority**: Capturing explicit turn-level sentiment is the core value of the feature and the minimum capability needed to support later analysis and quality improvement.

**Independent Test**: Can be fully tested by completing a chat turn, submitting a positive or negative rating on that specific response, and verifying that the system accepts the feedback without disrupting the active chat experience.

**Acceptance Scenarios**:

1. **Given** a user is viewing an agent response, **When** the user selects a positive rating control for that response, **Then** the system records that feedback for the exact response turn and keeps the chat experience responsive.
2. **Given** a user is viewing an agent response, **When** the user selects a negative rating control for that response, **Then** the system records that feedback for the exact response turn and preserves the response-to-feedback relationship.
3. **Given** a feedback submission is accepted, **When** the user continues chatting, **Then** the feedback capture does not interrupt or reset the active conversation session.
4. **Given** a user clicks a rating control, **When** that click occurs, **Then** the system immediately sends the rating submission through the feedback service boundary rather than waiting for the next chat turn.

---

### User Story 2 - Add Optional Context To Negative Feedback (Priority: P2)

As a user who marks a response negatively, I can optionally provide a short comment so the team has more actionable context about what went wrong.

**Why this priority**: A binary signal is useful, but optional user commentary makes negative feedback materially more diagnosable and valuable for future review.

**Independent Test**: Can be fully tested by submitting negative feedback, optionally entering a comment inline in the chat pane, dismissing the comment input when desired, and verifying that comments are captured only when supplied.

**Acceptance Scenarios**:

1. **Given** a user selects a negative rating for a response, **When** the feedback controls expand, **Then** the system shows an inline optional comment input associated with that same response.
2. **Given** the optional comment input is visible, **When** the user dismisses it without entering text, **Then** the system allows the user to leave only the negative rating.
3. **Given** the user enters comment text after the negative rating was already captured, **When** the comment is submitted, **Then** the system updates the same logical feedback record rather than creating a second ambiguous record for that response.

---

### User Story 3 - Capture Overall Experience Feedback (Priority: P3)

As a user, I can provide feedback about my overall chat experience from within the chat section even when I am not reacting to a specific assistant turn.

**Why this priority**: Turn-based feedback captures response quality, but overall-experience feedback captures broader satisfaction or friction that does not belong to one turn.

**Independent Test**: Can be fully tested by opening the chat area, invoking a low-profile overall-feedback affordance, confirming that the request flows through the existing CopilotKit and AG-UI chat/tool-call path, submitting an overall feedback card, and verifying the submission uses the same backend path while being labeled as a distinct feedback kind.

**Acceptance Scenarios**:

1. **Given** the overall-experience feedback feature is enabled, **When** the user views the chat section, **Then** the interface shows a basic, unintrusive affordance for opening overall feedback.
2. **Given** the user activates the overall-feedback affordance, **When** that action is triggered, **Then** the chat experience sends an in-chat request to give feedback through the normal CopilotKit and AG-UI flow rather than bypassing chat state with a separate immediate client-side submission.
3. **Given** the overall-feedback request enters the CopilotKit and AG-UI flow, **When** the agent/tool sequence responds, **Then** the chat displays an overall-feedback card within the conversation.
4. **Given** the overall-feedback card appears, **When** the user submits overall experience feedback, **Then** the feedback remains distinct from turn-based response feedback while still associating the submission with the turn represented by that feedback card.
5. **Given** an overall experience feedback submission is accepted, **When** it is stored and emitted, **Then** it uses the same backend feedback service boundary as turn-based feedback while remaining distinguishable by feedback kind.
6. **Given** the overall-experience feedback feature is disabled, **When** the user views the chat section, **Then** the overall-feedback affordance and card are not shown.

---

### User Story 4 - Analyze Feedback By Session And Turn (Priority: P4)

As an authorized product or operations stakeholder, I can retrieve feedback by session, turn, rating, and time range so I can analyze response quality alongside conversation and trace context.

**Why this priority**: Durable storage alone is insufficient unless feedback remains discoverable and correlated for evaluation, debugging, and service improvement workflows.

**Independent Test**: Can be fully tested by submitting feedback across multiple sessions and turns, then verifying that stored records can be filtered by session, turn, rating type, and time window while preserving correlation metadata.

**Acceptance Scenarios**:

1. **Given** feedback exists for multiple conversations and turns, **When** an authorized backend or admin analytics consumer filters feedback by session, **Then** the system returns only feedback associated with that session.
2. **Given** feedback exists for multiple responses, **When** an authorized backend or admin analytics consumer filters by turn, rating type, or time range, **Then** the system returns only records matching those filters.
3. **Given** a stored feedback record, **When** it is reviewed for analysis, **Then** it contains the identifiers needed to correlate it to the originating session, turn, and trace.

### Edge Cases

- What happens when a feedback submission is triggered for a response that is missing one or more required correlation identifiers? The system must reject the submission explicitly and avoid storing an uncorrelated record.
- What happens when a user submits negative feedback without a comment? The system must accept the rating without requiring explanatory text.
- What happens when the user opens the inline comment input and then dismisses it? The system must remove the input cleanly without obscuring nearby chat content or creating duplicate pending controls.
- What happens when the same response receives repeated feedback submissions from the same user? The system must keep one effective feedback record for that user and response, with the latest submission replacing the earlier one.
- What happens when a thumbs-down vote is captured immediately and the user later adds a comment? The system must update the same logical feedback record for that user and response rather than append a second independent record.
- What happens when a user provides overall experience feedback that is not tied to a single assistant response? The system must store it through the same feedback submission path while labeling it as a different feedback kind from turn-based feedback, and it may still associate the record with the turn represented by the feedback card.
- What happens when the user invokes overall feedback from the chat affordance? The system must route that request through the established CopilotKit and AG-UI conversational flow so the feedback card is produced through the same tool-call interaction model used elsewhere in chat.
- What happens when the overall-experience feedback feature is disabled? The system must hide the overall-feedback affordance and block overall-feedback submissions from that feature surface.
- What happens when durable storage succeeds but telemetry emission fails, or vice versa? The system must treat durable storage as the success boundary, attempt telemetry separately, and preserve enough status information for operators to detect, retry, and investigate the partial failure.
- What happens when the product is running in no-auth mode? The system must not show feedback controls and must not accept end-user feedback submissions in that mode.
- What happens when an end user attempts to query stored feedback records directly? The system must restrict feedback retrieval to authorized backend or admin analytics consumers and must not expose feedback query capability as a regular chat-user feature in the first release.
- What happens when a user includes sensitive or unexpected text in an optional feedback comment? In the first release, the system must store the comment as submitted subject only to general payload validity checks, because the feature is scoped as a demo or reference design for controlled enterprise settings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow users to submit explicit feedback on an individual agent response using the native CopilotKit thumbs-up/thumbs-down controls.
- **FR-002**: The system MUST also support overall experience feedback submitted from the chat interface independently of a specific assistant response.
- **FR-003**: The system MUST classify feedback by kind so turn-based response feedback and overall experience feedback remain distinguishable in storage, telemetry, and analytics.
- **FR-004**: The system MUST associate each feedback submission to the canonical conversation session identifier used by the product, where that session is the Foundry conversation identifier in the `conv_*` family.
- **FR-005**: The system MUST associate turn-based feedback submissions to the exact agent turn for the response being rated.
- **FR-006**: The system MUST associate each feedback submission to the corresponding trace identifier used for observability correlation when that identifier is available for the feedback kind being submitted.
- **FR-007**: The user interface MUST send feedback submissions through a backend feedback service boundary rather than storing feedback directly from the client.
- **FR-008**: Selecting a positive or negative rating control MUST trigger immediate feedback submission through the feedback service boundary rather than waiting for the next chat turn.
- **FR-009**: Invoking the overall-experience feedback affordance MUST send an in-chat feedback request through the existing CopilotKit and AG-UI conversational/tool-call flow used by the Microsoft Agent Framework integration.
- **FR-010**: The backend MUST validate that each feedback submission includes the required correlation identifiers and a valid feedback shape for its feedback kind before accepting it.
- **FR-011**: The exact required/optional field matrix per feedback kind is intentionally deferred to planning and MUST be codified in planning-phase contracts.
- **FR-012**: The backend MUST persist accepted feedback durably as the source of truth for later review and analytics.
- **FR-013**: The backend MUST emit a telemetry event for each accepted feedback submission so that feedback can be correlated with traces and service diagnostics.
- **FR-014**: A feedback record MUST include the submitting user identity when available, the conversation session identifier, the feedback kind, the optional comment, and the submission timestamp.
- **FR-015**: Turn-based feedback records MUST additionally include the turn identifier, trace identifier, and rating required to correlate them to a specific assistant response.
- **FR-016**: Overall experience feedback submitted through an in-chat feedback card MAY also include the identifier of the turn represented by that card, even though the feedback kind remains distinct from turn-based response feedback.
- **FR-017**: Users MUST be able to provide an optional free-text comment with negative feedback without being required to provide a comment for positive feedback.
- **FR-018**: When a user selects a negative rating, the chat interface MUST expose an inline optional comment input associated with that response and positioned so it does not overlap other visible chat content.
- **FR-019**: The inline comment input MUST be dismissible without losing the ability to submit rating-only negative feedback.
- **FR-020**: The chat section MUST provide a basic, unintrusive affordance for launching overall experience feedback when that feature is enabled.
- **FR-021**: Activating the overall-feedback affordance MUST initiate a CopilotKit and AG-UI-driven chat interaction that results in an in-chat overall-feedback card rather than rendering the card through a separate non-chat transport.
- **FR-022**: The system MUST support toggling the overall experience feedback feature on or off; when disabled, the overall-feedback affordance and submission card MUST NOT be shown.
- **FR-023**: The feedback submission flow MUST preserve the current chat session and MUST NOT interrupt the user’s ability to continue the conversation.
- **FR-024**: The system MUST keep at most one effective feedback record per user for the same response, and any later submission for that same response MUST replace the earlier submission so stored feedback remains unambiguous for analytics.
- **FR-025**: When a rating is captured first and a comment is submitted later for that same response, the system MUST treat the later submission as an idempotent update to the existing logical feedback record rather than creating a second independent record.
- **FR-026**: Exact idempotency key composition by feedback kind is intentionally deferred to planning and MUST be codified in planning-phase contracts.
- **FR-027**: Stored feedback MUST remain queryable by authorized backend or admin analytics consumers using conversation session, turn when applicable, rating type when applicable, feedback kind, and time range filters.
- **FR-028**: The system MUST preserve the correlation needed to link a turn-based feedback record to the exact agent turn, the Foundry-backed session, and the related observability trace.
- **FR-029**: Feedback storage and telemetry design MUST support future evaluation pipelines, dashboards, and model-improvement workflows without requiring redesign of the core feedback record.
- **FR-030**: Service-boundary validation contracts MUST cover feedback submission acceptance, correlation-field completeness, feedback-kind differentiation, durable persistence outcome, telemetry emission outcome, repeated-submission behavior, idempotent comment updates after immediate vote capture, overall-feedback turn association, AG-UI tool-call invocation for overall-feedback flows, and overall-feedback feature-toggle behavior.
- **FR-031**: Session continuity rules already established in the product MUST remain unchanged; feedback capture must attach to the existing canonical session identifier rather than introducing a parallel session key.
- **FR-032**: The system MUST retain sufficient operational visibility into partial failures so operators can distinguish between storage failure, telemetry failure, and successful dual-write completion.
- **FR-033**: Durable feedback storage MUST be the primary success boundary for submission acceptance; if storage succeeds and telemetry emission fails, the feedback submission MUST remain accepted and the system MUST mark the telemetry failure for operator visibility and retry handling.
- **FR-034**: Feedback capture controls and end-user feedback submission MUST be available only in authenticated mode; when authentication is disabled, the user interface MUST NOT render feedback controls and the system MUST NOT accept end-user feedback submissions from that mode.
- **FR-035**: The first release MUST restrict feedback retrieval capabilities to authorized backend or admin analytics consumers and MUST NOT expose a general end-user feedback query interface.
- **FR-036**: In the first release, optional feedback comments MUST be stored as submitted subject only to general payload validity checks, with no additional redaction or moderation requirement defined by this feature.
- **FR-037**: When feedback submission is not accepted because durable storage failed, the user interface MUST show a clear, non-blocking message that feedback was not saved and that the user may retry.
- **FR-038**: The user interface MUST NOT render an additional custom turn-response feedback card when the native CopilotKit response feedback controls are available; response feedback UX must remain a single, non-duplicated control set.

### Key Entities *(include if feature involves data)*

- **Feedback Submission**: A single user feedback action, whether tied to a specific response or submitted as overall experience feedback, including the feedback kind, optional comment, and submission time.
- **Feedback Correlation Link**: The identifier set that ties feedback to one canonical conversation session and, when applicable, one agent turn and one observability trace, including the turn represented by an overall-feedback card when that association exists.
- **Feedback Record**: The durable stored representation of accepted user feedback used for analysis and future evaluation workflows.
- **Feedback Outcome**: The resulting processing status of a submission, including whether durable storage and correlated telemetry both completed successfully.
- **Feedback Kind**: The category label that distinguishes turn-based rating feedback from overall experience feedback in storage, telemetry, and analytics.


## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of users can submit positive or negative feedback on a response in under 10 seconds from the time the response becomes visible.
- **SC-002**: At least 95% of accepted turn-based feedback submissions complete without introducing visible disruption to the active chat flow.
- **SC-003**: At least 95% of rating clicks result in an immediate feedback submission request without waiting for a subsequent chat turn.
- **SC-004**: At least 90% of users can locate and open the overall-experience feedback affordance in under 15 seconds when the feature is enabled.
- **SC-005**: At least 95% of overall-feedback affordance invocations enter the standard CopilotKit and AG-UI chat/tool-call flow and render an in-chat feedback card without requiring a non-chat fallback path.
- **SC-006**: 100% of accepted feedback records contain the conversation session identifier, feedback kind, optional comment field, and submission timestamp required for their feedback kind.
- **SC-007**: 100% of accepted turn-based feedback records contain the turn identifier, trace identifier, and rating required to correlate them to a specific assistant response.
- **SC-008**: 100% of accepted overall-feedback records submitted through an in-chat card retain the feedback kind distinction while also preserving the associated card-turn identifier when that association is present.
- **SC-009**: 100% of accepted feedback records can be retrieved through filters for session, turn when applicable, rating type when applicable, feedback kind, and time range.
- **SC-010**: At least 95% of negative-feedback comment submissions update the same durable feedback record as the earlier rating rather than creating a duplicate record.
- **SC-011**: 100% of stored turn-based feedback records remain correlatable to the originating Foundry conversation session and associated trace during validation sampling.
- **SC-012**: 100% of rejected feedback submissions lacking required correlation fields or feedback-kind-specific required fields are blocked from durable storage.
- **SC-013**: Operators can distinguish successful submission, storage-only failure, telemetry-only failure, and full failure outcomes for 100% of sampled submission-processing events.
- **SC-014**: At least 95% of submissions whose durable storage succeeds remain accepted even when telemetry emission is unavailable during validation scenarios that simulate telemetry failure.
- **SC-015**: 100% of no-auth validation runs show no feedback controls and no accepted end-user feedback submissions.
- **SC-016**: 100% of validation attempts by non-authorized consumers to retrieve stored feedback records are denied in the first release.
- **SC-017**: 100% of accepted optional feedback comments are durably stored exactly as submitted during validation sampling, excluding only submissions rejected for general payload invalidity.
- **SC-018**: 100% of validation runs with the overall-experience feedback feature disabled show no overall-feedback affordance or submission card in the chat section.
- **SC-019**: 100% of validation runs that simulate durable storage failure surface a user-visible feedback-save failure message without interrupting the active chat session.

## Assumptions

- The product continues to use the Foundry conversation identifier as the canonical session identifier for chat continuity, and feedback attaches to that existing session identity.
- Each user-visible agent response has enough metadata available at submission time to identify the associated conversation session, turn, and trace.
- Overall experience feedback is associated with the current conversation session and, when submitted through an in-chat feedback card, may also be associated with the turn represented by that card without being treated as turn-based response feedback.
- Existing authentication and user context mechanisms remain the basis for attaching user identity when it is available to the feedback flow.
- The first release focuses on response-level feedback capture and correlation, not on reviewer dashboards or automated downstream evaluation workflows.
- Durable feedback storage is separate from transient client state and remains suitable for long-term analysis.
- Queryability requirements apply only to authorized backend or admin analytics consumers and do not require a user-facing reporting interface in this feature.
- Inline comment entry is only required for the negative-feedback path in the first release.
- Rating clicks are captured immediately, and later comment submission updates the same logical feedback record rather than creating a separate feedback artifact.
- The overall-experience feedback affordance is presented within the chat section and can be enabled or disabled independently of turn-based feedback controls.
- The overall-experience feedback affordance initiates a normal CopilotKit and AG-UI chat/tool-call flow to produce the in-chat feedback card, rather than bypassing the chat interaction model.
- Exact per-kind required/optional field matrices and idempotency key shapes are intentionally finalized during planning contracts, not at clarification level.
- Durable storage is treated as authoritative for submission acceptance, while telemetry delivery may complete asynchronously after acceptance when needed.
- No-auth mode is treated as outside the supported scope for end-user feedback capture in the first release.
- This feature is scoped as a demo or reference design intended for controlled enterprise settings, so no separate comment-redaction or moderation workflow is required in the first release.