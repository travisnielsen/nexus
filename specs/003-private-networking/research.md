# Research: Private Networking

## Decision 1: Cadence Terraform layout is the authoritative file-organization target
- Decision: Reorganize `infra/` from the current coarse layout (`main.tf`, `workload.tf`, etc.) to a concern-split layout mirroring Cadence `infra/terraform` naming and separation (`networking.tf`, `security.tf`, `ai-platform.tf`, `compute.tf`, `devops.tf`, `observability.tf`, `utility.tf`, plus shared `providers.tf`, `variables.tf`, `outputs.tf`).
- Rationale: The feature clarification explicitly makes Cadence structure authoritative. This improves discoverability and aligns cross-repo operational practices.
- Alternatives considered:
  - Keep current `workload.tf` monolith and only add private resources: rejected due to explicit requirement to mirror Cadence structure.
  - Adopt AVM-first custom structure: rejected because AVM is guidance, not structure authority.
- Sources:
  - Cadence repo structure via GitHub API listing (`fetch_webpage` on `api.github.com/repos/travisnielsen/cadence/contents/infra/terraform`)
  - Spec clarifications in `specs/003-private-networking/spec.md`

## Decision 2: Use BYO private dependencies for Foundry VNET-injected outbound model
- Decision: Treat Foundry deployment as BYO private dependencies (Cosmos DB, Storage, AI Search where applicable), with Foundry private endpoint for inbound and delegated subnet for outbound VNET injection.
- Rationale: Microsoft Foundry network-isolation guidance requires private endpoint + VNET injection constraints and private endpoint setup for dependent PaaS resources.
- Alternatives considered:
  - Keep Foundry public and only secure app workloads: rejected due to FR-002/FR-011 requirements.
  - Private inbound only without outbound VNET injection: rejected due to explicit feature requirement.
- Sources:
  - Microsoft Learn Foundry network isolation (`fetch_webpage` on `learn.microsoft.com/azure/ai-foundry/how-to/configure-private-link`)

## Decision 3: Keep ACR public network access enabled for GitHub-hosted runner compatibility
- Decision: Keep ACR public network access enabled (possibly with constrained policy in later hardening), as an explicit prerequisite for public runner CI/CD in this feature.
- Rationale: Clarified requirement and known hosted-runner network variability make private-endpoint-only ACR incompatible with this phase.
- Alternatives considered:
  - Private-endpoint-only ACR: rejected due to public runner requirement.
  - Self-hosted runners in VNET: rejected for this feature scope.
- Sources:
  - Spec clarification entries
  - Microsoft Learn ACR network access behavior (`fetch_webpage` on `learn.microsoft.com/azure/container-registry/container-registry-access-selected-networks`)

## Decision 4: Container Apps environment remains VNET-integrated with selective public ingress at app level
- Decision: Deploy container apps in VNET-integrated environment and preserve app-level public ingress only for frontend and logistics; logistics-data and recommendations remain internal.
- Rationale: Satisfies private topology while preserving required public entry points.
- Alternatives considered:
  - All apps public: rejected security scope.
  - Internal environment with no public ingress: rejected because frontend/logistics must stay public.
- Sources:
  - Microsoft Learn Container Apps networking (`fetch_webpage` on `learn.microsoft.com/azure/container-apps/networking`)
  - Feature requirements FR-003/FR-004

## Decision 5: Add Terraform-to-GitHub variable sync script under infra scripts and document as operational prerequisite
- Decision: Introduce a script equivalent to Cadence `update-github-vars-from-terraform.sh` to map Terraform outputs to GitHub repository variables, with idempotent diff reporting and Foundry-variable updates.
- Rationale: Reduces deployment drift and enforces post-refactor variable consistency.
- Alternatives considered:
  - Manual variable updates in runbooks: rejected due to drift risk and SC-008.
  - CI-only one-way update without local operator use: rejected due to troubleshooting and reproducibility needs.
- Sources:
  - Spec requirements FR-012/FR-013/FR-014/FR-016
  - Cadence reference script requirement from feature input

## Decision 6: Preserve AG-UI/CopilotKit behavior and MCP data-path boundaries as non-functional invariants
- Decision: Treat frontend chat behavior and MCP data mediation as invariants; networking/IaC changes must not alter application interaction semantics.
- Rationale: Constitution principles and feature FR-009/FR-010 require no behavior regression.
- Alternatives considered:
  - Rewire data path directly to private data stores from frontend/backend: rejected by constitution and spec.
- Sources:
  - Nexus constitution (`.specify/memory/constitution.md`)
  - AG-UI/CopilotKit repo evidence (`semantic_search` excerpt from `src/frontend/src/app/page.tsx`, `src/frontend/src/components/*`, `media/docs/ag-ui-features.md`)

## Decision 7: Use Microsoft Agent Framework Python path conventions already in repo
- Decision: Keep Python async, typed, boundary-validating patterns for logistics and recommendations services while changing infra topology.
- Rationale: Matches active repository implementation and MAF skill guidance; avoids introducing framework-level churn during infrastructure refactor.
- Alternatives considered:
  - Agent runtime refactor concurrent with networking: rejected as out of scope and high regression risk.
- Sources:
  - MAF skill guidance (`.github/skills/microsoft-agent-framework/SKILL.md`)
  - Existing backend structure under `src/backend/logistics`

## Decision 8: Keep logistics public ingress for SPA direct-call compatibility in this feature
- Decision: Keep `logistics` publicly reachable in this feature scope, while preserving internal-only ingress for `logistics-data` and `recommendations`.
- Rationale: For a browser-based React SPA, API calls originate from client browsers, not Container App VNET egress. Without introducing a server-side proxy/BFF path, private-only logistics ingress would break direct browser access patterns (including streaming endpoints).
- Alternatives considered:
  - Make logistics internal-only now: rejected because no server-side proxy/BFF introduction is in 003 scope.
  - Add proxy/BFF in this feature: rejected as out of scope for the current infra-focused refactor.
- Sources:
  - Feature clarification captured in `specs/003-private-networking/spec.md`

## Decision 9: Use NAT Gateway as explicit outbound egress for required public endpoints
- Decision: Configure Azure NAT Gateway on applicable workload subnets so in-scope services can reach required public internet/public Microsoft endpoints without relying on default outbound access.
- Rationale: Microsoft guidance indicates new VNets/subnets are private by default in newer API behavior, which means explicit outbound is needed for public endpoints. NAT Gateway is the recommended explicit outbound method for most scenarios and is supported for Azure Container Apps workload profile environments.
- Alternatives considered:
  - Rely on default outbound behavior: rejected due to non-deterministic behavior and private-subnet defaults.
  - Use only firewall/NVA egress in this feature: deferred; valid alternative but broader operational scope than required for 003.
- Sources:
  - Microsoft Learn default outbound access guidance (`fetch_webpage` on `learn.microsoft.com/azure/virtual-network/ip-services/default-outbound-access`)
  - Microsoft Learn NAT Gateway overview (`fetch_webpage` on `learn.microsoft.com/azure/nat-gateway/nat-overview`)
  - Microsoft Learn Azure Container Apps networking (`fetch_webpage` on `learn.microsoft.com/azure/container-apps/networking`)

## Clarification Resolution Status
- No unresolved `NEEDS CLARIFICATION` markers remain in the feature spec.

## Revalidation Log
- 2026-05-30: Revalidated outbound networking assumptions against first-party Microsoft Learn guidance for default outbound access changes, NAT Gateway explicit egress, and Container Apps networking support.

## Migration Scope Notes
- Dashboard deployment workflow remains retired from active CI/CD in this feature scope.
- Dashboard-related static website infrastructure compatibility outputs are intentionally retained to avoid cross-feature breakage while 003 focuses on networking and Terraform concern-split migration.
- Cadence concern ownership remains authoritative; AVM usage is adapted to that structure rather than dictating file organization.

## Research Source Validation
- MAF-related findings reference: `.github/skills/microsoft-agent-framework/SKILL.md`.
- CopilotKit/AG-UI findings include repository exploration evidence from semantic/code search tooling.
- Azure platform findings are grounded in Microsoft Learn pages fetched from `learn.microsoft.com`.
- Note: Dedicated `mcp_azure_mcp_documentation` tool was unavailable in this session; first-party Microsoft Learn sources were used directly via `fetch_webpage`.
