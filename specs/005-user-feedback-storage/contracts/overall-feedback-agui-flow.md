# Contract: Overall Feedback AG-UI Tool-Call Flow

## Intent
Ensure overall experience feedback is initiated and rendered through the standard CopilotKit + AG-UI conversational/tool-call flow, while submission still uses the shared backend feedback service boundary.

## Trigger and Flow
1. User activates overall-feedback affordance in chat section.
2. Frontend sends in-chat request through CopilotKit runtime.
3. Backend agent path emits AG-UI tool-call events for overall-feedback card rendering.
4. Frontend renders overall-feedback card in conversation stream.
5. User submits card feedback.
6. Frontend calls `POST /logistics/feedback` with `feedback_kind=overall_experience`.
7. Backend validates, upserts durable record, emits telemetry, returns outcome.

## Event/Contract Expectations
- Flow must use standard AG-UI tool-call lifecycle semantics.
- No non-chat side channel should render the overall card when feature is enabled.
- Session continuity remains on canonical `conv_*` conversation identity.
- Overall feedback card may include optional `card_turn_id` correlation.

## Payload Requirements for Overall Submission
Required:
- `feedback_kind=overall_experience`
- `conversation_id`
- `rating`
- `source_surface=overall_feedback_card`

Optional:
- `comment`
- `card_turn_id`
- `trace_id` when available

## Feature Toggle Behavior
- Toggle ON: affordance visible; AG-UI flow active.
- Toggle OFF: affordance and card hidden; no submission from disabled surface.

## Failure Behavior
- AG-UI rendering failure before submission: no persistence attempt.
- Submission failure after card submit: user receives backend error response; no accepted record unless storage succeeded.
- Storage success plus telemetry failure: accepted response with telemetry-failed status.
