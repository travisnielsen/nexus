# Validation: Zero-Turn Session Suppression (T065)

## Objective

Confirm zero-turn conversations are not visible in session history.

## Checks

| Check | Expected Outcome | Result | Evidence |
| --- | --- | --- | --- |
| Fresh conversation created without user turn | Not shown in history | | |
| Immediate open history after page load | Zero-turn entry not shown | | |
| After first persisted user turn | Session becomes eligible for history | | |

## Final Status

- Status: PASS / FAIL
- Notes:
