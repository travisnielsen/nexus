# Implementation Plan: Private Networking

**Branch**: `003-private-networking` | **Date**: 2026-05-30 | **Spec**: `specs/003-private-networking/spec.md`

**Input**: Feature specification from `/specs/003-private-networking/spec.md`

## Summary

Implement a private-networking infrastructure baseline for Nexus while preserving required public entry points and CI/CD behavior. The solution will: (1) make Cosmos DB private, (2) deploy Foundry with private endpoint + VNET injection outbound access, (3) provide explicit outbound egress for required public endpoints via NAT Gateway on applicable subnets, (4) keep container apps in VNET with selective public ingress (frontend/logistics only), (5) add utility VM, (6) keep ACR public network access for public GitHub-hosted runner compatibility, (7) add Terraform-output-to-GitHub-variable sync automation, and (8) reorganize Terraform files to mirror Cadence `infra/terraform` as the authoritative structure.

## Technical Context

**Language/Version**: Terraform 1.x (IaC), Bash/PowerShell for infra automation, Python 3.12+ and TypeScript/Node 20 remain unchanged runtime stacks.

**Primary Dependencies**: AzureRM Terraform provider, Azure Container Apps, Azure Cosmos DB, Azure AI Foundry resources, Azure Container Registry, GitHub Actions variables, existing monorepo `uv`/`npm` toolchains.

**Storage**: Azure Cosmos DB (private endpoint), Azure Storage for Terraform state and Foundry BYO resources.

**Testing**: `terraform fmt`, `terraform validate`, targeted plan diff checks, `uv run --project . poe check`, `npm run lint` when frontend docs/config touched.

**Target Platform**: Azure subscription deployment via GitHub Actions public runners and local operator workflows.

**Project Type**: Monorepo web application + infrastructure-as-code.

**Performance Goals**: No user-visible regression in AG-UI/CopilotKit interactions; CI/CD success >= spec SC-003; variable sync reliability >= SC-007/SC-008.

**Constraints**:
- Cadence `infra/terraform` structure is authoritative.
- ACR public network access must remain enabled in this feature.
- Operational data path remains MCP-mediated.
- AVM guidance is applied within (not instead of) Cadence structure.
- Remove Azure Static Website dashboard deployment workflow from CI/CD scope, but keep dashboard static website infrastructure resources out of 003 migration/restructure scope.
- Because frontend is a browser SPA in this feature, logistics ingress remains public unless/until a dedicated server-side proxy/BFF path is introduced.
- Do not rely on default outbound access behavior for in-scope egress; use explicit outbound configuration (NAT Gateway) for required public endpoints.

**Scale/Scope**: `infra/**`, deployment workflows/variables, documentation updates, and compatibility checks across logistics/logistics-data/recommendations + frontend chat behavior.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Phase 0 Gate
- [x] Data path integrity: feature keeps operational dashboard data on MCP-mediated paths.
- [x] No direct product-path SQL or Azure AI Search dependency introduced for core flight data.
- [x] Boundary contracts are explicitly typed and validated (Pydantic/TypeScript interfaces).
- [x] AG-UI + CopilotKit interaction compatibility is preserved and test coverage identified.
- [x] Quality gates and observability impact are captured (`uv run --project . poe check`, `npm run lint`, Terraform checks).

### Post-Phase 1 Re-check
- [x] Design artifacts preserve MCP-only operational data path.
- [x] Contracts explicitly define ingress/exposure and variable-sync boundaries.
- [x] Quickstart includes required quality gates and validation commands.
- [x] No constitution violations require exception handling.

## Project Structure

### Documentation (this feature)

```text
specs/003-private-networking/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── networking-and-exposure-contract.md
│   └── terraform-output-github-variable-sync-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
infra/
├── providers.tf
├── variables.tf
├── outputs.tf
├── locals.shared.tf                # add if needed for shared naming/locals
├── networking.tf                   # Cadence-authoritative domain split
├── security.tf
├── ai-platform.tf
├── compute.tf
├── devops.tf
├── observability.tf
├── utility.tf
├── terraform.tfvars
├── backend.hcl.example             # add if missing
└── scripts/
    └── update-github-vars-from-terraform.sh

.github/workflows/
├── deploy-logistics.yml
├── deploy-logistics-data.yml
├── deploy-recommendations.yml
└── deploy-frontend.yml

media/docs/
├── dev-setup.md
├── getting-started.md
└── coding-standard.md
```

**Structure Decision**: Use existing monorepo layout and refactor `infra/` into Cadence-aligned domain files. Preserve resource intent while moving definitions from aggregate files into domain-specific files.

## Complexity Tracking

No constitution violations identified; section not applicable.
