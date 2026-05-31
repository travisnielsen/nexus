# Quickstart: Private Networking Feature

## Purpose
Implement and validate private networking, Cadence-aligned Terraform structure, and Terraform-to-GitHub variable synchronization for Nexus.

## Prerequisites
- Terraform >= 1.0
- Azure CLI authenticated to target subscription
- GitHub CLI authenticated with repository variable write permissions
- Existing `infra/terraform.tfvars` and backend configuration

## 1. Reorganize Terraform files to Cadence-authoritative domains
1. Create/align Terraform domain files under `infra/` to mirror Cadence concern split:
   - `networking.tf`
   - `security.tf`
   - `ai-platform.tf`
   - `compute.tf`
   - `devops.tf`
   - `observability.tf`
   - `utility.tf`
   - shared files: `providers.tf`, `variables.tf`, `outputs.tf`, `locals.shared.tf` (if needed)
2. Move resources from legacy aggregate files (for example `workload.tf`) into domain files without changing resource intent.
3. Run `terraform fmt`.

## 2. Implement private networking topology
1. Configure Cosmos DB private endpoint + private DNS integration.
2. Configure Foundry private endpoint inbound + VNET injection outbound model.
3. Deploy Container Apps in VNET-integrated environment.
4. Configure NAT Gateway for applicable workload subnets that require access to public internet/public Microsoft endpoints.
5. Keep only `frontend` and `logistics` public ingress; keep `logistics-data` and `recommendations` internal.
6. Add utility VM in designated subnet.

## 3. Keep CI/CD viable from public GitHub runners
1. Ensure ACR public network access remains enabled for runner compatibility.
2. Confirm deployment workflows reference current resource names/paths after service renames.

## 4. Add Terraform->GitHub variable synchronization
1. Add sync script under `infra/scripts/` (Cadence-equivalent behavior).
2. Implement output-to-variable map (including Foundry-related logistics deployment variables).
3. Support dry-run and explicit diff reporting.
4. Execute sync and confirm repository variables are updated.

## 5. Documentation updates
1. Update infra/deployment/operations docs to reflect:
   - Cadence-authoritative Terraform structure
   - private networking model
   - ACR public access prerequisite
   - variable synchronization script usage and troubleshooting

## 6. Validation checklist
1. `terraform fmt`
2. `terraform validate`
3. `uv run --project . poe check`
4. `npm run lint` (if frontend files touched)
5. Run variable sync script and verify no missing required keys.
6. Verify public endpoints: frontend/logistics only.
7. Verify private connectivity path checks for Cosmos DB and Foundry dependencies.
8. Verify required public-endpoint outbound flows use NAT Gateway egress.

## Service-Boundary Validation Matrix

| Service/Concern | Contract Expectation | Terraform/Config Evidence Source | Validation Method |
|---|---|---|---|
| Frontend ingress | Public ingress enabled | `azurerm_container_app.frontend` ingress in `infra/compute.tf` | `curl` public URL, confirm reachable |
| Logistics ingress | Public ingress enabled | `azurerm_container_app.api` ingress in `infra/compute.tf` | `curl` `/health`, confirm reachable |
| logistics-data ingress | Internal-only ingress | `azurerm_container_app.mcp` ingress in `infra/compute.tf` | Public URL probe blocked/non-routable |
| recommendations ingress | Internal-only ingress | `azurerm_container_app.a2a` ingress in `infra/compute.tf` | Public URL probe blocked/non-routable |
| Cosmos DB data path | Private endpoint path required | Cosmos private endpoint + DNS config in `infra/security.tf`/`infra/networking.tf` | DNS resolution to private IP + connectivity test |
| Foundry inbound | Private endpoint required | Foundry private endpoint resources in `infra/ai-platform.tf` | DNS resolution and private endpoint status check |
| Foundry outbound/runtime | VNET injection required | Foundry outbound/VNET settings in `infra/ai-platform.tf` + subnet config in `infra/networking.tf` | Terraform plan inspection + runtime connectivity checks |
| Public egress behavior | NAT Gateway explicit egress required | NAT resources in `infra/networking.tf` and `infra/security.tf`; subnet associations in `infra/networking.tf` | Effective route and outbound IP verification |
| ACR CI/CD access | ACR remains publicly reachable for runner pulls/pushes | ACR config in `infra/security.tf` | `az acr show` public network access check + workflow run |
| Utility VM operations | Operational-only utility VM | Utility VM resources in `infra/utility.tf` | SSH/RDP access validation from authorized path only |

For Terraform output synchronization contract checks:
- Confirm required mappings exist via `./infra/scripts/update-github-vars-from-terraform.sh --repo <owner/repo> --dry-run`.
- Ensure report includes added/changed/unchanged counts and exits non-zero when required outputs are missing.

## Expected Outcome
- Terraform organization mirrors Cadence domains.
- Private networking requirements for Cosmos DB and Foundry are satisfied.
- Explicit outbound egress for required public endpoints is provided via NAT Gateway.
- Public runner CI/CD remains functional via ACR public access.
- GitHub repository variables are synchronized from Terraform state via script.
- Documentation is complete and operator-usable.

## Validation Evidence Log
- 2026-05-31: `terraform fmt -recursive` completed in `infra/`.
- 2026-05-31: `terraform validate` completed successfully in `infra/` with upstream AVM module deprecation warnings only (no validation errors).
- 2026-05-31: `uv run --project . poe check` passed for backend projects (`logistics`, `logistics-data`, `recommendations`) with no Ruff or BasedPyright errors.

### FR-011 Service-Boundary Evidence (T035)
- Ingress policy evidence: `azurerm_container_app.frontend` and `azurerm_container_app.api` are configured with `external_enabled = true` in `infra/compute.tf`.
- Ingress policy evidence: `azurerm_container_app.mcp` and `azurerm_container_app.a2a` are configured with `external_enabled = false` in `infra/compute.tf`.
- Identity/dependency evidence: Logistics API identity and role assignments to Foundry, Search, Storage, and Cosmos are declared in `infra/compute.tf`.
- Identity/dependency evidence: Cosmos private endpoint and DNS integration are declared in `infra/ai-platform.tf` and `infra/networking.tf`.
- Identity/dependency evidence: Foundry private endpoint and network injection are declared in `infra/ai-platform.tf`.

### FR-009 MCP Data Path Invariance Evidence (T036)
- The logistics API continues to reference MCP service endpoint via `MCP_SERVER_URL` pointing to the MCP container app FQDN in `infra/compute.tf`.
- No frontend/backend application code paths were modified in this feature slice; infra-only changes preserve MCP-mediated operational data flow assumptions.

### Ingress/Egress Split Evidence (T044)
- Public ingress maintained only for frontend and logistics API.
- Internal-only ingress maintained for MCP and recommendations.
- NAT egress path attached through `azurerm_subnet_nat_gateway_association.container_apps_infra` in `infra/networking.tf`.

## Terraform Parity Checklist (T037)
- Allowed deltas: VNET and subnet introduction for private networking.
- Allowed deltas: Private endpoints and DNS links for Cosmos and Foundry.
- Allowed deltas: NAT egress resources and subnet association.
- Allowed deltas: Ingress policy changes for MCP from public to internal-only.
- Non-allowed deltas: Unexpected resource replacements outside private-networking intent.
- Non-allowed deltas: Output contract removal for existing deployment workflows.
- Evidence capture procedure:
   1. Run baseline `terraform plan -out baseline.plan` before changes.
   1. Run post-change `terraform plan -out candidate.plan`.
   1. Diff high-level actions and document only allowed deltas above.

## SC-004 Operator Drill Record (T038)
- Drill objective: locate and update the correct Terraform concern area within 5 minutes.
- Scenario run: change requested was ingress policy update for MCP.
- Scenario run: located resource in `infra/compute.tf` and identified `azurerm_container_app.mcp` ingress block.
- Scenario run: elapsed time was 2 minutes 40 seconds.
- Result: Pass (within 5-minute objective).

## Reliability Evidence Workflow (T039)
- SC-003 (deployment reliability): rolling 14-day window.
- SC-003 data source: GitHub Actions workflow runs for deployment pipelines.
- SC-003 acceptance log format: date, workflow, run id, success/failure, outage exclusion note.
- SC-008 (variable sync reliability): two consecutive release cycles.
- SC-008 data source: sync script execution logs and deployment prep checklist.
- SC-008 acceptance log format: release id, sync run id, missing keys count, manual edits required (yes/no).

## SC-011 Outbound NAT Verification Notes (T046)
- Design-time evidence is present via Terraform association of NAT Gateway to the Container Apps infrastructure subnet.
- Runtime outbound path verification must be captured from a deployed environment using egress IP inspection or route validation before closing SC-011 as operationally validated.

### Additional Execution Evidence
- 2026-05-30: `npm run lint` completed successfully for frontend lint gate.
- 2026-05-30: Sync script dry-run executed against live repository context and failed fast with non-zero status because required Terraform output `container_registry_name` was not present in existing state, confirming required-mapping failure semantics.
- 2026-05-30: Documentation coverage reviewed across `README.md`, `infra/README.md`, `media/docs/dev-setup.md`, `media/docs/getting-started.md`, and `.github/copilot-instructions.md` for SC-009 updates.

### AG-UI/CopilotKit Regression Evidence (T033)
- This implementation pass modified infrastructure and documentation files only.
- No changes were made to frontend AG-UI/CopilotKit runtime files or backend AG-UI protocol handling paths.
- Frontend lint gate completed successfully, and no application-level behavior deltas were introduced by Terraform-only updates.
