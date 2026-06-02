# Validation: US3 Artifact Rehydration (T050)

## Objective

Verify supported AG-UI artifacts rehydrate correctly and unsupported artifacts degrade gracefully without transcript loss.

## Scenario Matrix

| Scenario | Expected Outcome | Result | Evidence |
| --- | --- | --- | --- |
| Supported artifact resume | Artifact restored in correct transcript position | PASS (code path) | Backend manifest builder emits `restored` entries with `transcript_index` and descriptor for supported subset: `tool_result_text`, `assistant_tool_call_summary` in `src/backend/logistics/services/session_service.py`. Frontend hydrator sorts by `transcriptIndex` and renders ordered cards in `src/frontend/src/lib/sessionArtifactHydration.ts` and `src/frontend/src/components/SessionHistoryFlyout.tsx`. |
| Unsupported artifact resume | Fallback notice shown, transcript remains usable | PASS (code path) | Backend emits `unsupported`/`missing_data` with fallback text in `src/backend/logistics/services/session_service.py`; frontend renders non-blocking fallback notices in `src/frontend/src/components/SessionHistoryFlyout.tsx`. |
| Multiple artifact session | Order preserved and no side-effect replay | PASS (code path) | Hydrator is read-only and explicitly avoids executing tools/side effects; see comment and implementation in `src/frontend/src/lib/sessionArtifactHydration.ts`. Ordered rendering uses `transcriptIndex` ascending. |

## FR/SC Coverage

- FR-011, FR-012, FR-013
- SC-005

## Final Status

- Status: PASS (implementation contract)
- Notes:
	- Runtime verification completed for session history rendering and resume flow in local dev (user-observed).
	- User-provided runtime screenshot confirms rich artifact cards are rehydrated in the flyout/session history flow (supported subset visible in UI).
	- Additional targeted manual capture with an explicit unsupported artifact case can be appended for release evidence screenshots/logs.
