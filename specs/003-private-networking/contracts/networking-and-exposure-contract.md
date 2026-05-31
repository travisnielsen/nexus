# Contract: Networking and Exposure

## Scope
- `infra/**` Terraform resources for networking, container apps ingress, Foundry, Cosmos DB, and utility VM.
- Deployment surfaces consumed by frontend, logistics, logistics-data, recommendations.

## Contract Requirements
1. Service ingress policy
- `frontend` and `logistics` MUST expose public ingress.
- `logistics-data` and `recommendations` MUST be internal-only.

1. Private dependencies
- Cosmos DB MUST use private endpoint path.
- Foundry MUST use private endpoint for inbound and VNET injection for outbound dependency reachability.

1. Runtime placement
- Container Apps workloads MUST be deployed in VNET-integrated environment.

1. Explicit outbound egress
- Workloads that require public internet/public Microsoft endpoint access MUST use explicit outbound egress via NAT Gateway on applicable subnets.
- Design MUST NOT rely on default outbound access behavior for in-scope workloads.

1. ACR access mode
- ACR public network access MUST remain enabled for public GitHub-hosted runner CI/CD in this feature.

1. Utility VM
- Utility VM MUST be deployed in designated network segment and remain operational-only.

## Verification
- Terraform plan shows expected ingress flags and private endpoint resources.
- Smoke checks verify public routes only for frontend/logistics.
- Private DNS and endpoint validation confirms private path to Cosmos/Foundry dependencies.
- Validation confirms required public-endpoint outbound traffic uses NAT Gateway egress.
