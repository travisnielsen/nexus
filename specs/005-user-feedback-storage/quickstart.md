# Quickstart: User Feedback Storage

## Purpose
Validate end-to-end behavior for turn feedback and overall-experience feedback with durable storage, telemetry correlation, and authorized retrieval.

## Prerequisites
- Backend API running from `src/backend/logistics`.
- Frontend running from `src/frontend`.
- Auth enabled for validation runs that include feedback capture.
- Cosmos DB connectivity configured for backend service credentials.
- Application Insights/OpenTelemetry configured for telemetry validation.

## Run Services
From repo root:

```bash
npm run dev
```

Or run services individually:

```bash
cd src/backend/logistics && uv run uvicorn main:app --port 8000 --reload
cd src/frontend && npm run dev:ui
```

## Validation Flows

### Flow A: Immediate turn feedback (thumbs)
1. Open chat and submit a prompt.
2. Wait for an assistant response.
3. Click thumbs-up or thumbs-down for that response.
4. Confirm immediate submission request dispatch at click time.
5. Continue chatting; verify no session reset and no visible interruption.

Expected:
- Accepted response from backend.
- Durable record created or updated via idempotency key.
- Telemetry attempted with correlation fields.

### Flow B: Negative feedback with optional comment
1. Submit thumbs-down.
2. Confirm inline optional comment input appears for that response.
3. Submit with no comment.
4. Submit again for same response with comment.
5. Confirm same logical record is updated (latest-write-wins), not duplicated.

Expected:
- One effective record per user and response.
- Comment stored as submitted.

### Flow C: Overall experience feedback via AG-UI tool-call path
1. Ensure overall-feedback feature toggle is enabled.
2. In chat section, use overall-feedback affordance.
3. Confirm chat/tool-call flow renders overall feedback card.
4. Submit overall feedback from the card.
5. Verify record persisted with `feedback_kind=overall_experience` and optional card-turn association.

Expected:
- Overall flow uses chat interaction model, not side-channel rendering.
- Same backend feedback boundary accepts submission.

### Flow D: Feature-toggle off behavior
1. Disable overall-feedback feature toggle.
2. Refresh chat.
3. Verify overall-feedback affordance and card are not shown.
4. Attempt direct UI-based overall submission from disabled surface.

Expected:
- Surface hidden.
- Submission blocked from disabled UI flow.

### Flow E: Auth and access constraints
1. Run app in authenticated mode; verify feedback controls available.
2. Run app with no-auth mode; verify feedback controls hidden.
3. Attempt feedback submission in no-auth mode.
4. Attempt feedback retrieval as non-admin consumer.

Expected:
- No-auth mode does not allow end-user feedback capture.
- Retrieval is denied for unauthorized consumers.

## Query Validation (Authorized Backend/Admin)
Validate filtering over stored records by:
- conversation id (`conv_*`)
- kind (`turn_response`, `overall_experience`)
- rating
- turn id where applicable
- time range

Expected:
- Records are filterable without ambiguity.
- Turn feedback records contain required turn and trace correlation fields.

## Telemetry and Partial Failure Validation
1. Simulate telemetry emission failure while keeping storage available.
2. Submit feedback.
3. Confirm submission remains accepted when storage succeeds.
4. Confirm telemetry failure is observable in outcome/status logs.

Expected:
- Acceptance boundary remains storage success.
- Operators can distinguish `storage_succeeded + telemetry_failed`.

## Suggested Local Checks

```bash
uv run --project . poe check
cd src/frontend && npm run lint
```

## Success Criteria Mapping
- Immediate submission and no interruption: SC-001, SC-002, SC-003.
- Overall-flow discoverability and AG-UI invocation: SC-004, SC-005, SC-018.
- Correlation field completeness: SC-006, SC-007, SC-008, SC-011.
- Queryability and access controls: SC-009, SC-015, SC-016.
- Idempotent update behavior: SC-010.
- Validation and partial-failure observability: SC-012, SC-013, SC-014.
- Comment storage policy: SC-017.
