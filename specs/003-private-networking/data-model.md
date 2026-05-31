# Data Model: Private Networking

## Entity: TerraformDomainFile
- Description: Canonical file in the Cadence-authoritative Terraform domain split.
- Fields:
  - `name` (string): Filename (for example `networking.tf`, `security.tf`).
  - `domain` (enum): `networking|security|ai-platform|compute|devops|observability|utility|shared`.
  - `authoritative_source` (string): Cadence path mapped to local path.
  - `resources` (array[string]): Resource addresses owned by this file.
  - `dependencies` (array[string]): Upstream resource/file dependencies.
- Validation rules:
  - `domain` must map to one of Cadence domains.
  - Files marked `shared` are limited to providers/variables/outputs/locals concerns.

## Entity: ServiceExposurePolicy
- Description: Public/private ingress policy for each deployed runtime service.
- Fields:
  - `service_name` (enum): `frontend|logistics|logistics-data|recommendations`.
  - `environment_scope` (string): Container Apps environment identifier.
  - `ingress_scope` (enum): `public|internal`.
  - `allowed_origins_or_sources` (array[string], optional).
- Validation rules:
  - `frontend` and `logistics` must be `public`.
  - `logistics-data` and `recommendations` must be `internal`.

## Entity: PrivateDependencyBinding
- Description: Private routing contract between runtime services and private dependencies.
- Fields:
  - `source_service` (string): Calling service.
  - `target_dependency` (enum): `cosmosdb|foundry|storage|search|acr|other-private-service`.
  - `path_type` (enum): `private-endpoint|vnet-injection|internal-vnet-route`.
  - `dns_zone` (string, optional): Private DNS zone used for resolution.
  - `status` (enum): `planned|provisioned|validated`.
- Validation rules:
  - `cosmosdb` bindings require `private-endpoint`.
  - Foundry outbound bindings require `vnet-injection` in this feature.

## Entity: OutboundEgressPolicy
- Description: Defines explicit outbound behavior for workloads that must reach public endpoints.
- Fields:
  - `source_scope` (string): Subnet or workload scope using the policy.
  - `egress_method` (enum): `nat-gateway|firewall|nva`.
  - `nat_gateway_resource_id` (string, optional): Required when `egress_method=nat-gateway`.
  - `covered_destinations` (array[string]): Public destinations/service tags requiring explicit outbound.
  - `status` (enum): `planned|provisioned|validated`.
- Validation rules:
  - In-scope public endpoint egress must use an explicit method and must not depend on default outbound access.
  - When `egress_method=nat-gateway`, `nat_gateway_resource_id` must be present.

## Entity: UtilityVmProfile
- Description: Operational utility VM deployed in VNET for diagnostics/admin workflows.
- Fields:
  - `vm_name` (string)
  - `subnet_id` (string)
  - `access_method` (enum): `bastion|jumpbox|vpn`.
  - `purpose` (string): operational use case.
  - `managed_identity_enabled` (boolean)
- Validation rules:
  - Must not be declared as required data path for application runtime.

## Entity: GithubVariableSyncMap
- Description: Mapping of Terraform outputs to GitHub Actions repository variables.
- Fields:
  - `terraform_output` (string)
  - `github_variable` (string)
  - `required` (boolean)
  - `category` (enum): `deploy_url|resource_name|auth|foundry|telemetry|networking`.
  - `last_synced_at` (datetime, optional)
- Validation rules:
  - Required mappings must exist before deployment workflow execution.
  - Foundry-related mappings must include renamed fields needed by logistics after client migration.

## Entity: SyncExecutionReport
- Description: Result of one variable synchronization script run.
- Fields:
  - `run_id` (string)
  - `dry_run` (boolean)
  - `changed_keys` (array[string])
  - `unchanged_keys` (array[string])
  - `missing_required_keys` (array[string])
  - `exit_status` (enum): `success|partial|failure`
  - `timestamp` (datetime)
- Validation rules:
  - `missing_required_keys` must be empty for successful release-prep runs.

## Relationships
- `TerraformDomainFile` 1..n -> 0..n `PrivateDependencyBinding` (files define networking/resource bindings).
- `ServiceExposurePolicy` 1..1 per service -> governs ingress for runtime workloads.
- `OutboundEgressPolicy` 1..n -> `PrivateDependencyBinding` (explicit outbound policy complements private endpoint routes when public egress is required).
- `GithubVariableSyncMap` 1..* -> `SyncExecutionReport` (reports validate mapping correctness over time).
- `UtilityVmProfile` participates in validation/troubleshooting flows but not product runtime data path.
