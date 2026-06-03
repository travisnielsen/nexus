# Validation Index: Agent Session Persistence

## Purpose

This folder captures functional test evidence for feature 004. Use this index as the execution order and traceability map between requirements, tasks, and evidence artifacts.

## Execution Order

1. `us-cross-local-auth-e2e.md`
2. `us1-resume-prior-session.md`
3. `us2-session-management.md`
4. `us3-artifact-rehydration.md`
5. `us-cross-agui-compatibility.md`
6. `us-cross-authz-privacy.md`
7. `us-cross-network-boundary.md`
8. `us-cross-cosmos-bootstrap.md`
9. `us-cross-local-cache-sync.md`
10. `us-cross-transcript-source-contract.md`
11. `us-cross-zero-turn-filter.md`
12. `us-cross-noauth-history-gating.md`
13. `us-cross-mcp-path-integrity.md`
14. `us-cross-performance-sync-metrics.md`
15. `quality-gates.md`
16. `final-quality-gate.md`

## Requirement and Success Criteria Coverage Matrix

| Key | Evidence File(s) |
| --- | --- |
| FR-001, FR-002 | `us1-resume-prior-session.md` |
| FR-003 | `us2-session-management.md` |
| FR-004, FR-005, FR-006 | `us1-resume-prior-session.md`, `us-cross-local-auth-e2e.md` |
| FR-007 | `us-cross-transcript-source-contract.md`, `us-cross-network-boundary.md` |
| FR-008, FR-009, FR-010 | `us2-session-management.md` |
| FR-011, FR-012, FR-013 | `us3-artifact-rehydration.md` |
| FR-014 | `us-cross-agui-compatibility.md` |
| FR-015 | `us-cross-authz-privacy.md` |
| FR-016 | `us-cross-mcp-path-integrity.md` |
| FR-017 | `us-cross-transcript-source-contract.md`, `us-cross-authz-privacy.md`, `us-cross-agui-compatibility.md` |
| FR-018, FR-019, FR-020 | `us1-resume-prior-session.md`, `us2-session-management.md` |
| FR-021, FR-022, FR-023, FR-024 | `us-cross-local-cache-sync.md`, `us2-session-management.md` |
| FR-025 | `us-cross-zero-turn-filter.md` |
| FR-026 | `us-cross-noauth-history-gating.md` |
| SC-001, SC-002, SC-003 | `us1-resume-prior-session.md`, `us-cross-local-auth-e2e.md` |
| SC-004 | `us2-session-management.md` |
| SC-005 | `us3-artifact-rehydration.md` |
| SC-006 | `us-cross-authz-privacy.md` |
| SC-007, SC-008 | `us1-resume-prior-session.md`, `us2-session-management.md` |
| SC-009, SC-010 | `us-cross-performance-sync-metrics.md` |
| SC-011 | `us-cross-zero-turn-filter.md` |
| SC-012 | `us-cross-noauth-history-gating.md` |

## Minimum Acceptance Bar

1. All required evidence files exist and have a final status.
2. No failed result in any MUST requirement validation.
3. Quality gates pass and outputs are captured.
4. Signed-in local E2E lifecycle test is completed at least once end-to-end.
5. No-auth gating test and zero-turn suppression test both pass.
