# Research: Repository Stable Version Upgrade

## Decision 1: Migrate backend chat client to Foundry-native `FoundryChatClient`

- Decision: Replace legacy/pre-release Azure compatibility client usage (`agent_framework.azure.AzureAIClient`) with `agent_framework.foundry.FoundryChatClient` in `src/backend/logistics/clients.py` for the primary logistics agent runtime path.
- Rationale: Microsoft Learn and MAF guidance indicate Python Foundry-first paths now live under `agent_framework.foundry`, and older Azure AI compatibility surfaces have been removed in current APIs. This aligns with future Foundry v2 native/hosted adoption.
- Alternatives considered:
  - Keep `AzureAIClient`: rejected due to deprecation/removal risk and mismatch with current Foundry-first guidance.
  - Switch directly to `FoundryAgent` now: rejected as primary default because current app-owned instructions/tools architecture in `logistics_agent.py` maps better to `Agent(client=FoundryChatClient(...))`; `FoundryAgent` remains a planned extension path for service-managed definitions.
- Sources:
  - MAF skill: `.github/skills/microsoft-agent-framework/SKILL.md`, `.github/skills/microsoft-agent-framework/references/python.md`
  - Microsoft Learn MCP docs: `mcp_azure_mcp_documentation` (Foundry provider docs, upgrade notes)

## Decision 2: Add Foundry package alignment in Python dependencies

- Decision: Upgrade backend dependency sets toward current stable `agent-framework-*` packages and include `agent-framework-foundry` for Foundry-native clients; remove reliance on old provider-specific compatibility surfaces where possible.
- Rationale: Foundry-first Python clients are package-split and provider-led; keeping old compatibility packages conflicts with long-term v2 hosted features and may block upgrades.
- Alternatives considered:
  - Leave dependency set unchanged and only update code: rejected because lockfile/graph would still retain stale APIs and block future migration.
  - Full hosted-agent-only stack now: deferred; current architecture still needs app-owned tool execution path.
- Sources:
  - MAF skill: `.github/skills/microsoft-agent-framework/SKILL.md`
  - Microsoft Learn MCP docs: `mcp_azure_mcp_documentation` (Python significant changes + Foundry provider config)

## Decision 3: Preserve AG-UI/CopilotKit protocol behavior during upgrade

- Decision: Keep AG-UI lifecycle/tool/state streaming semantics and existing `use_service_session=True` thread continuity behavior unchanged while dependencies are upgraded.
- Rationale: This feature is a version-upgrade effort; preserving tool-call and state synchronization contracts prevents UI regressions.
- Alternatives considered:
  - Refactor AG-UI event behavior during dependency upgrade: rejected as out-of-scope and high regression risk.
- Sources:
  - CopilotKit MCP tools: `mcp_copilotkit_mc_search-ag-ui-docs`, `mcp_copilotkit_mc_search-ag-ui-code`
  - Repository context: `.github/copilot-instructions.md`, `src/backend/logistics/agents/logistics_agent.py`

## Decision 4: Lockfile and transitive strategy

- Decision: Regenerate lockfiles when direct dependency upgrades require graph changes and accept required transitive updates, then run full regression validation.
- Rationale: For modern Python/Node ecosystems, forcing old transitive trees with upgraded direct dependencies increases breakage/security risk.
- Alternatives considered:
  - Freeze transitive versions: rejected due to conflict risk and hidden CVE debt.
- Sources:
  - Spec clarifications in `spec.md`
  - MAF/Azure best-practices guidance (`mcp_azure_mcp_get_azure_bestpractices`)

## Decision 5: Unsupported dependency handling

- Decision: If no direct successor exists, replace with stable maintained substitute or establish an in-repo maintained fork in-scope for this feature.
- Rationale: User-selected policy requires completion of upgrade scope without deferrals.
- Alternatives considered:
  - Defer unsupported dependencies: rejected by clarified requirements.
- Sources:
  - Spec clarifications in `spec.md`

## Decision 6: Latest-supported version enforcement

- Decision: For each dependency upgrade task, target the latest supported stable version verified at execution time using authoritative sources.
- Rationale: Prevents upgrades that are stale, deprecated, or outside support windows.
- Execution policy:
  - Validate support status using first-party docs, official release notes, or SDK source repositories.
  - If latest-supported adoption is blocked, use highest supported compatible version and record blocker plus follow-up.
- Sources:
  - `.github/skills/microsoft-agent-framework/SKILL.md`
  - Microsoft Learn via `mcp_azure_mcp_documentation`

## Decision 7: Replacement implementation must be executable, not record-only

- Decision: Unsupported dependency handling requires actual implementation updates in manifests/code plus equivalence validation, with records produced afterward.
- Rationale: Documentation-only replacements do not satisfy feature requirements.
- Sources:
  - Feature requirements FR-012 in `spec.md`
  - Task remediation updates in `tasks.md`

## Implementation Notes for Foundry v2-readiness

- Keep the default runtime on `FoundryChatClient` for app-owned instructions/tools.
- Design the client factory so a future hosted path can swap to `FoundryAgent` with minimal API churn.
- Ensure environment variable naming follows Foundry guidance (`FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_MODEL`) while preserving compatibility mapping from existing project env vars during migration.
- Preserve telemetry and async credential handling patterns already in use.
