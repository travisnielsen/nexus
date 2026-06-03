# Frontend (Next.js + CopilotKit)

This frontend hosts the Logistics Explorer dashboard and Copilot chat experience.

## Session History UX (Local-First)

Session history is intentionally local-first for responsiveness while remaining backend-authoritative for durability.

### Behavior Summary

- Session flyout is available only in authenticated mode.
- Session APIs are called through Next.js proxy routes under `/api/sessions/**`.
- Browser localStorage is hydrated first at startup, then background sync reconciles with backend state.
- Rename/delete operations are applied optimistically in UI and then reconciled to backend results.
- Mutation status badges indicate `pending`, `synced`, or `failed` state per session.
- Session switching is blocked while an agent run is active.
- Zero-turn sessions are excluded from visible history.

### Session API Proxy Routes

- `GET /api/sessions` -> backend `/api/sessions`
- `GET /api/sessions/{sessionId}` -> backend `/api/sessions/{sessionId}`
- `PATCH /api/sessions/{sessionId}` -> backend rename mutation
- `DELETE /api/sessions/{sessionId}` -> backend delete mutation

All session requests forward the bearer token to preserve user-scoped authorization.

### Artifact Rehydration (US3)

- Backend returns `restoration_status` (`full|partial|none`) and `restoration_manifest`.
- Frontend hydrator converts the manifest into:
  - restored artifact cards (supported subset)
  - fallback notices (unsupported/missing)
- Hydration is read-only and does not execute tool side effects.

## Development

```bash
cd src/frontend
npm run dev
```

## Quality Gate

```bash
cd src/frontend
npm run lint
```
