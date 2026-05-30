# US2 Upgrade Regressions Found

Date: 2026-05-29

## Summary

Regressions were detected during post-upgrade quality-gate execution and remediated.

## Regressions

1. API type-check import failure
- Signal: `Import "pydantic_settings" could not be resolved`
- Scope: `src/backend/logistics/middleware/auth.py`
- Root cause: dependency became non-transitive after upgrades.
- Remediation: added direct dependency `pydantic-settings>=2.14.1` in API manifest and regenerated lockfile.
- Status: resolved.

1. A2A service SDK API incompatibility
- Signal: multiple basedpyright failures in `src/backend/recommendations/main.py` with `a2a-sdk` 1.x.
- Root cause: current service code targets pre-1.0 A2A SDK surface.
- Remediation: constrained recommendations project dependency to `a2a-sdk[http-server]>=0.3.25,<1.0.0` and regenerated lockfile.
- Status: resolved.

1. Frontend lint peer-compatibility warning
- Signal: npm peer warnings when using ESLint 10 with current `eslint-config-next`.
- Root cause: peer dependency window currently supports ESLint 9.
- Remediation: switched to compatible `eslint^9.39.4`.
- Status: resolved.

1. API startup regression after dependency cleanup
- Signal: API failed at startup with `ImportError: aiohttp package is not installed`.
- Root cause: async Azure credential transport path requires aiohttp; package had been removed during lockfile refresh.
- Remediation: added direct dependency `aiohttp>=3.13.2` to `src/backend/logistics/pyproject.toml` and regenerated `src/backend/logistics/uv.lock`.
- Status: resolved.

1. Frontend CopilotKit/AG-UI runtime regression
- Signal: browser console errors `agent_connect_failed` and `agent_run_failed_event` with `TypeError: e is not a function` during chat run path.
- Root cause: AG-UI client version mismatch (`@ag-ui/client` forced to `0.0.54`) against CopilotKit 1.59.1 dependency set (`0.0.53`).
- Remediation: aligned override to `@ag-ui/client@0.0.53`, reinstalled dependencies, and revalidated end-to-end chat + tool flows.
- Status: resolved.

## Current State

- Python monorepo checks now pass.
- Frontend lint/build now pass.
- Conversation bootstrap now succeeds after firewall changes.
- Critical regression gate re-run passes with end-to-end AG-UI/CopilotKit flows validated.
