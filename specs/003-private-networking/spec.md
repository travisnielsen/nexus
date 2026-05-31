# Feature Specification: Private Networking

**Feature Branch**: `[003-private-networking]`

**Created**: 2026-05-30

**Status**: Draft

**Input**: User description: "Create a new feature spec for private networking. For this repo, use the same pattern demonstrated in the Cadence reference environment. Cosmos DB must be private, Foundry must be deployed into a private VNET with outbound VNET-injected access to private services, Container Apps must be deployed in the VNET, frontend and logistics Container Apps must remain publicly accessible, add a utility VM, keep CI/CD working with public GitHub runners, and switch Terraform file organization to match Cadence structure."

## Clarifications

### Session 2026-05-30

- Q: What is the required Azure Container Registry access model for CI/CD with public GitHub runners? -> A: Azure Container Registry must allow public network access as a prerequisite for using public GitHub-hosted runners.
- Q: How should GitHub Actions environment variables stay aligned with Terraform state outputs for this environment? -> A: Add Cadence-style synchronization from Terraform outputs to GitHub repository variables, including updates required for recent Foundry client migration changes in logistics.
- Q: What documentation scope is required for this feature? -> A: Perform full documentation updates and explicitly document the variable synchronization script in existing repository docs.
- Q: Which Terraform structure has final authority when AVM recommendations differ from existing reference structure? -> A: The current Cadence `infra/terraform` structure is authoritative and must be mirrored; AVM agent guidance should be applied within that structure rather than replacing it.
- Q: Is Azure Static Website dashboard deployment included in this private-networking refactor scope? -> A: The dashboard deployment workflow should be removed as part of this refactor, while dashboard static website infrastructure resources remain out of scope for migration/restructure in 003.
- Q: Can the logistics API be private-only if the frontend is a React SPA? -> A: Not for direct browser calls. SPA traffic originates from the client browser (not Container App VNET egress), so logistics must remain publicly reachable in this feature unless a server-side proxy/BFF path is introduced.
- Q: Do we need NAT Gateway for outbound connectivity from private subnets in this feature? -> A: Yes for public endpoints. New VNets/subnets are private by default, so workloads that must reach internet or public Microsoft endpoints need explicit egress; this feature uses NAT Gateway as the standard outbound method.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Private Service Connectivity Baseline (Priority: P1)

As a platform engineer, I can deploy the backend data and AI dependencies inside private networking boundaries so sensitive service-to-service traffic never traverses public endpoints.

**Why this priority**: This is the core security and compliance objective and enables all downstream networking decisions.

**Independent Test**: Can be fully tested by deploying only networking plus data/AI services and verifying private connectivity paths for Cosmos DB and Foundry from in-VNET workloads.

**Acceptance Scenarios**:

1. **Given** a new environment deployment, **When** Cosmos DB is provisioned, **Then** it is reachable only through private networking paths and not through unrestricted public access.
2. **Given** Foundry is deployed with VNET injection, **When** it needs outbound access to private dependencies, **Then** access succeeds through private VNET-routed paths.
3. **Given** backend services are deployed into the VNET, **When** they access private dependencies, **Then** those calls succeed without requiring public data-plane exposure.

---

### User Story 2 - Controlled Public Exposure (Priority: P2)

As an application owner, I can keep user-facing access where needed while preserving private-only access for internal services.

**Why this priority**: The product must stay usable externally while minimizing unnecessary exposure.

**Independent Test**: Can be fully tested by validating ingress behavior per service after deployment without requiring advanced telemetry tooling.

**Acceptance Scenarios**:

1. **Given** all containerized services are deployed in the VNET, **When** ingress is evaluated, **Then** frontend and logistics endpoints are publicly reachable while internal-only services remain private.
2. **Given** a request is sent directly to an internal service endpoint, **When** the request originates from the public internet, **Then** access is denied.

---

### User Story 3 - Maintainable Terraform and Delivery Pipeline (Priority: P3)

As a platform engineer, I can manage infrastructure through a Terraform file organization that mirrors the Cadence environment pattern while still deploying from public GitHub-hosted runners.

**Why this priority**: Long-term maintainability and delivery reliability are required for ongoing operations.

**Independent Test**: Can be fully tested by running the infrastructure plan/apply workflow from public runners and confirming equivalent outputs after the file reorganization.

**Acceptance Scenarios**:

1. **Given** the Terraform configuration has been reorganized by concern to mirror the Cadence pattern, **When** an engineer performs routine changes, **Then** they can identify where to update networking, service deployment, and output definitions without ambiguity.
2. **Given** CI/CD runs from public GitHub runners, **When** infrastructure deployment is triggered, **Then** the pipeline completes successfully without requiring self-hosted runners.
3. **Given** the utility VM is part of the deployment scope, **When** the environment is provisioned, **Then** the VM is deployed in the intended network segment and available for administrative utility tasks.

### Edge Cases

- What happens when private DNS or endpoint associations are incomplete during deployment? The deployment must fail with explicit diagnostics that identify which dependency path is unresolved.
- How does the system handle temporary outbound restrictions from VNET-injected services to private dependencies? Retry behavior must avoid partial success states and report actionable errors.
- What happens if public ingress is unintentionally enabled for an internal-only service? Validation must detect and block the deployment before release.
- What happens when Terraform reorganization changes file boundaries but not intended resource behavior? Plan validation must confirm no unintended destructive changes are introduced.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provision Cosmos DB with private network access controls that prevent unrestricted public data-plane access.
- **FR-002**: The system MUST deploy Foundry with private VNET integration that supports outbound connectivity to privately exposed dependencies, including Cosmos DB.
- **FR-003**: The system MUST deploy Container Apps within the VNET so internal service-to-service and dependency traffic can use private networking paths.
- **FR-004**: The system MUST expose only the frontend and logistics Container Apps for public ingress and MUST keep internal service endpoints private.
- **FR-005**: The system MUST deploy a utility VM in the designated network boundary for operational access and maintenance workflows.
- **FR-006**: The infrastructure delivery workflow MUST remain executable from public GitHub-hosted runners, and Azure Container Registry MUST allow public network access so those runners can push and pull deployment images.
- **FR-007**: Terraform configuration MUST be reorganized to mirror the current Cadence `infra/terraform` structure as the authoritative reference pattern for this repository.
- **FR-008**: The infrastructure definitions MUST preserve existing environment behavior and outputs after reorganization, except for intentional private-networking changes defined in this feature.
- **FR-009**: Operational data access requirements MUST continue to route through MCP service interfaces after networking changes.
- **FR-010**: AG-UI and CopilotKit user interaction behavior MUST remain functionally unchanged by networking and infrastructure file reorganization.
- **FR-011**: Service-boundary validation contracts MUST confirm connectivity, ingress policy, and identity assumptions between logistics, logistics-data, recommendations, Foundry, and Cosmos DB.
- **FR-012**: The system MUST provide an automation script pattern equivalent to the Cadence `update-github-vars-from-terraform.sh` workflow that synchronizes required GitHub Actions repository variables from current Terraform outputs.
- **FR-013**: The synchronization process MUST update GitHub Actions variables needed by logistics service deployment after the Foundry client migration, including any renamed, added, or retired Foundry-related variables.
- **FR-014**: Synchronization MUST be idempotent and MUST report explicit differences between Terraform outputs and current GitHub variable values before and after update.
- **FR-015**: The implementation MUST include full documentation updates across existing infrastructure, deployment, and operations documentation to reflect private networking, Terraform reorganization, and CI/CD variable synchronization behavior.
- **FR-016**: Existing documentation MUST include a dedicated section for the Terraform-to-GitHub variable synchronization script, covering purpose, prerequisites, required permissions, execution steps, and troubleshooting guidance.
- **FR-017**: When AVM agent recommendations conflict with Cadence repository structure decisions, the implementation MUST preserve Cadence structural conventions and adapt AVM usage to fit that structure.
- **FR-018**: The implementation MUST remove the dashboard deployment workflow (`.github/workflows/deploy-dashboard.yml`) from active CI/CD while keeping dashboard static website infrastructure resources out of 003 migration/restructure scope.
- **FR-019**: The implementation MUST provide explicit outbound egress for required public endpoints by attaching Azure NAT Gateway to the applicable workload subnets in the VNET-integrated deployment.
- **FR-020**: The implementation MUST document which dependencies use private endpoints versus NAT-based public egress and MUST validate that required outbound flows succeed without relying on default outbound access.

### Key Entities *(include if feature involves data)*

- **Service Exposure Profile**: Defines whether each deployed service is public or private and the permitted ingress boundary.
- **Private Dependency Route**: Represents approved private connectivity paths between in-VNET workloads and private platform dependencies.
- **Terraform Organization Domain**: A concern-based grouping of infrastructure definitions (networking, shared platform resources, application workloads, and outputs) aligned to the Cadence reference pattern.
- **Pipeline Execution Context**: Defines the constraints and required access model for CI/CD execution from public GitHub-hosted runners.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of production-intended traffic from logistics, recommendations, and logistics-data services to Cosmos DB and Foundry uses private connectivity paths.
- **SC-002**: 100% of internal-only services are non-publicly reachable, while frontend and logistics remain publicly reachable.
- **SC-003**: Infrastructure deployment from public GitHub-hosted runners succeeds in at least 95% of runs across a two-week validation window, excluding external provider outages.
- **SC-006**: 100% of successful CI/CD runs from public GitHub-hosted runners can authenticate to Azure Container Registry and complete required image push/pull operations without private-runner dependencies.
- **SC-007**: On each sync execution, 100% of required deployment variables derived from Terraform outputs are present and correctly updated in GitHub repository variables for the target environment.
- **SC-008**: Variable synchronization runs complete with zero manual GitHub variable edits required during release preparation for at least two consecutive release cycles.
- **SC-009**: Documentation review confirms 100% of impacted existing docs are updated, and the variable synchronization script is documented with executable operator steps and validation guidance.
- **SC-010**: Terraform file and directory organization in this repository matches the current Cadence `infra/terraform` layout for corresponding concerns, with any intentional deviations documented and approved.
- **SC-004**: Engineers can locate and update the correct Terraform concern area (networking, platform dependencies, app workloads, outputs) within 5 minutes during an operations drill.
- **SC-005**: Post-reorganization plan validation shows zero unintended resource replacements outside explicitly approved private-networking changes.
- **SC-011**: 100% of required outbound calls to public internet/public Microsoft endpoints from targeted workloads originate through the configured NAT Gateway egress path.

## Assumptions

- The Cadence `infra/terraform` repository structure is available and treated as the authoritative structural baseline for this feature.
- Existing identity and secret-management patterns continue to be used unless explicitly changed in a follow-up feature.
- Public ingress requirements remain limited to frontend and logistics for this phase; a private-only logistics endpoint requires a separate feature that introduces a server-side proxy/BFF path.
- Private DNS and network prerequisites needed for private service connectivity are permitted in target subscriptions.
- Utility VM usage is operational and administrative only, not an application runtime dependency.
- CI/CD authentication from public GitHub runners remains based on federated identity with appropriate Azure role assignments.
- Azure Container Registry public network access is intentionally enabled to support public GitHub-hosted runner access.
- The repository has permission and token scope to update GitHub repository variables through automation.
- Azure Static Website dashboard infrastructure resources remain managed outside this feature and are intentionally not migrated/restructured by 003 tasks.
- Subnets/workloads in scope that require access to public endpoints will use explicit outbound egress via NAT Gateway instead of default outbound behavior.
