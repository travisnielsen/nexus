# Contract: AG-UI Artifact Rehydration and Transcript Fallback

## Purpose

Define restoration guarantees for previously generated AG-UI artifacts when loading historical sessions.

## Contract 1: Supported Subset Declaration

- Requirements:
  - v1 must define an explicit supported subset of artifact types for restoration.
  - Supported subset definition is versioned and owned by feature code.
  - Every artifact in history is evaluated against this subset at load time.

## Contract 2: Deterministic Placement

- Requirements:
  - Restored artifacts must render at the same logical transcript position as original generation.
  - Restoration must preserve parent message linkage (message/tool-call correlation).
  - Rendering order must remain stable across reloads.

## Contract 3: Restoration Descriptor Validation

- Requirements:
  - Supported artifacts require a typed restoration descriptor payload.
  - Missing or invalid descriptor data transitions artifact to non-restored state.
  - Descriptor validation failures must not block transcript loading.

## Contract 4: Fallback Behavior

- Requirements:
  - Unsupported or failed restoration cases must preserve transcript continuity.
  - UI must show an explicit, user-visible fallback notice for each non-restored artifact.
  - Fallback rendering must not break input, scrolling, or subsequent turn submission.

## Contract 5: Partial Restoration Signaling

- Requirements:
  - Session load response must include aggregate restoration status (`full`, `partial`, `none`).
  - Frontend must surface partial restoration state once per load in a non-blocking way.

## Contract 6: Safety and Compatibility

- Requirements:
  - Artifact restoration cannot alter CopilotKit/AG-UI behavior for newly generated turns.
  - Restoration logic must avoid replaying side effects (no duplicate tool mutation execution).
  - Active streaming and historical restoration flows remain isolated.

## Validation Gates

- Required checks:
  - Supported artifact restoration success cases.
  - Unsupported artifact fallback cases.
  - Missing-data fallback cases.
  - Regression checks for normal new-chat interactions.
