# Validation: US1 Resume Prior Session (T031)

## Objective

Verify session browsing, load, transcript continuity, context continuity, unavailable-state behavior, and active-run switch blocking.

## Scenario Matrix

| Scenario | Expected Outcome | Result | Evidence |
| --- | --- | --- | --- |
| Latest 20 ordered list with date/time | Correct ordering and metadata | | |
| Select prior session | Transcript loads in chat | | |
| Follow-up after resume | Continues same conversation context | | |
| Switch while active run | Switch blocked or explicit cancel required | | |
| Unavailable session | Visible but non-resumable with clear state | | |

## FR/SC Coverage

- FR-001, FR-002, FR-004, FR-005, FR-006, FR-018, FR-019, FR-020
- SC-001, SC-002, SC-003, SC-007, SC-008

## Final Status

- Status: PASS / FAIL
- Notes:
