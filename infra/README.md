# Infrastructure Deployment

This directory contains Terraform configuration for deploying Nexus to Azure.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) >= 2.50
- An Azure subscription with permissions to create resources
- Azure AD permissions to create App Registrations

## Azure Resources Created

| Resource | Purpose |
|----------|---------|
| Container Apps Environment | Hosts backend, frontend, and MCP containers |
| Container App (API) | Backend FastAPI + MAF agent |
| Container App (Frontend) | Next.js dashboard |
| Container App (MCP) | MCP server with DuckDB |
| Container Registry | Stores Docker images |
| AI Foundry Hub + Project | Azure AI services and model deployments |
| Application Insights | Telemetry and distributed tracing |
| Log Analytics Workspace | Centralized logging |

## Step 1: Create App Registrations

Before deploying infrastructure, create the required Azure AD App Registrations:

### Frontend App Registration

```bash
# Create the frontend app registration
az ad app create \
  --display-name "nexus-frontend" \
  --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "http://localhost:3000" "https://<your-frontend-url>"

# Note the Application (client) ID - you'll need this for NEXT_PUBLIC_AZURE_AD_CLIENT_ID
```

### Backend API App Registration

```bash
# Create the backend API app registration
az ad app create \
  --display-name "nexus-backend-api" \
  --sign-in-audience AzureADMyOrg

# Note the Application (client) ID - you'll need this for backend_api_app_client_id
# Also define an API scope in the app registration, such as access_as_user,
# and note the full scope URI for backend_api_scope_uri.
# Example: api://<backend-api-client-id>/access_as_user
```

### MCP App Registration (Optional - for MCP authentication)

```bash
# Create the MCP app registration
az ad app create \
  --display-name "nexus-mcp" \
  --sign-in-audience AzureADMyOrg

# Note the Application (client) ID - you'll need this for mcp_app_client_id
```

### GitHub Actions Service Principal (for CI/CD)

```bash
# Create the service principal
az ad sp create-for-rbac \
  --name "github-actions-nexus" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group>

# Note the Object ID - you'll need this for github_actions_principal_id
```

## Step 2: Set Up Remote State Storage

Terraform state is stored remotely in Azure Blob Storage so it can be shared across machines.

### One-time setup (per Azure subscription)

Create a resource group and storage account for state files:

```bash
az group create -n rg-terraform-state -l westus3
az storage account create -n <unique-storage-account-name> -g rg-terraform-state -l westus3 --sku Standard_LRS
az storage container create -n tfstate --account-name <unique-storage-account-name>
```

### Per-machine setup

Create a `backend.hcl` file in this directory (not committed to source control):

```hcl
storage_account_name = "<unique-storage-account-name>"
```

## Step 3: Configure Variables

Start from the example file and then fill in environment-specific values:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Key variables in `terraform.tfvars`:

```hcl
subscription_id             = "<your-subscription-id>"
region                      = "westus3"
region_aifoundry            = "eastus2"
frontend_app_client_id      = "<frontend-app-registration-client-id>"
backend_api_app_client_id   = "<backend-api-app-registration-client-id>"
backend_api_scope_uri       = "api://<backend-api-app-registration-client-id>/access_as_user"
mcp_app_client_id           = "<mcp-app-registration-client-id>"
github_actions_principal_id = "<github-actions-sp-object-id>"
auth_enabled                = true  # Set to false for development
```

## Step 4: Deploy Infrastructure

```bash
# Login to Azure
az login

# Initialize Terraform (pass backend config)
terraform init -backend-config=backend.hcl

# Preview changes
terraform plan

# Apply changes
terraform apply
```

## Step 5: Note Output Values

After deployment, Terraform outputs important values needed for configuration:

```bash
terraform output
```

Key outputs:
- `frontend_url` - URL for the deployed frontend
- `api_url` - URL for the deployed API
- `mcp_url` - URL for the deployed MCP server
- `appinsights_instrumentation_key` - Instrumentation key for frontend telemetry
- `appinsights_ingestion_endpoint` - Ingestion endpoint for frontend telemetry

## Cleaning Up

To destroy all resources:

```bash
terraform destroy
```

## Troubleshooting

### Authentication Issues

If you see authentication errors:
1. Ensure `az login` is current
2. Verify your account has sufficient permissions
3. Check that App Registration client IDs are correct

### Region Availability

Some Azure services (like AI Foundry) are only available in specific regions. The default configuration uses:
- `westus3` for general resources
- `eastus2` for AI Foundry resources

Adjust `region` and `region_aifoundry` variables if needed.

## Terraform to GitHub Variable Sync

Use `infra/scripts/update-github-vars-from-terraform.sh` to synchronize selected Terraform outputs into GitHub repository variables used by deployment workflows.

Requirements:
- `terraform`
- `gh` with authenticated session (`gh auth login`)

Usage:

```bash
cd infra
./scripts/update-github-vars-from-terraform.sh --repo <owner/repo> --dry-run
./scripts/update-github-vars-from-terraform.sh --repo <owner/repo>
```

Execution permissions:

```bash
chmod +x ./scripts/update-github-vars-from-terraform.sh
```

Mapped variables:
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_CONTAINER_REGISTRY`
- `AZURE_API_CONTAINER_APP_NAME`
- `AZURE_FRONTEND_CONTAINER_APP_NAME`
- `AZURE_MCP_CONTAINER_APP_NAME`
- `AZURE_A2A_CONTAINER_APP_NAME`
- `AGENT_API_BASE_URL`
- `FOUNDRY_PROJECT_ENDPOINT`
- `NEXT_PUBLIC_AZURE_AD_CLIENT_ID`
- `NEXT_PUBLIC_AZURE_AD_TENANT_ID`
- `NEXT_PUBLIC_AZURE_AD_API_SCOPE_URI`
- `NEXT_PUBLIC_AUTH_ENABLED`
- `AUTH_ENABLED`

Script behavior:
- Idempotent update logic (`added`, `changed`, `unchanged` summary)
- Dry-run preview without mutating GitHub variables
- Non-zero exit for missing required Terraform outputs or GitHub update failures

Troubleshooting:
- `GitHub CLI is not authenticated`: run `gh auth login` and retry.
- Missing Terraform output mapping errors: run `terraform output -json | jq keys` and verify required outputs exist.
- Variable update permission errors: ensure token/user has repository `Actions: write` access.

## Private Endpoint DNS and Validation Runbook

This environment uses private endpoints for in-scope data-plane dependencies and links private DNS zones to the workload VNET.

Current private DNS zones:
- `privatelink.blob.core.windows.net` (Storage account)
- `privatelink.documents.azure.com` (Cosmos DB SQL)
- `privatelink.cognitiveservices.azure.com` (Azure AI Foundry account)
- `privatelink.openai.azure.com` (Azure AI Foundry account)
- `privatelink.services.ai.azure.com` (Azure AI Foundry endpoint)

Post-deployment validation flow:

```bash
# 1) Confirm private DNS zones and VNET links
az network private-dns zone list -g "$(terraform output -raw resource_group_name)" -o table
az network private-dns link vnet list -g "$(terraform output -raw resource_group_name)" -z privatelink.blob.core.windows.net -o table
az network private-dns link vnet list -g "$(terraform output -raw resource_group_name)" -z privatelink.documents.azure.com -o table
az network private-dns link vnet list -g "$(terraform output -raw resource_group_name)" -z privatelink.cognitiveservices.azure.com -o table
az network private-dns link vnet list -g "$(terraform output -raw resource_group_name)" -z privatelink.openai.azure.com -o table
az network private-dns link vnet list -g "$(terraform output -raw resource_group_name)" -z privatelink.services.ai.azure.com -o table

# 2) Confirm private endpoints are provisioned and connected
az network private-endpoint list -g "$(terraform output -raw resource_group_name)" -o table

# 3) Confirm Container Apps exposure model
az containerapp show -g "$(terraform output -raw resource_group_name)" -n "$(terraform output -raw frontend_container_app_name)" --query 'properties.configuration.ingress.external' -o tsv
az containerapp show -g "$(terraform output -raw resource_group_name)" -n "$(terraform output -raw api_container_app_name)" --query 'properties.configuration.ingress.external' -o tsv
az containerapp show -g "$(terraform output -raw resource_group_name)" -n "$(terraform output -raw mcp_container_app_name)" --query 'properties.configuration.ingress.external' -o tsv
az containerapp show -g "$(terraform output -raw resource_group_name)" -n "$(terraform output -raw a2a_container_app_name)" --query 'properties.configuration.ingress.external' -o tsv
```

Expected results:
- Storage, Cosmos DB, and Foundry private endpoint resources exist and are in `Approved` connection state.
- Frontend and logistics API ingress are public (`true`).
- MCP and recommendations ingress are internal-only (`false`).

If the utility VM still shows a private-access warning in the Foundry portal, verify private DNS resolution from that VM first. Foundry networking is validated through private endpoint reachability and DNS, not a subnet-based portal allow-list.

## NAT Egress Operator Guidance

Design intent:
- Workloads requiring public endpoint access egress through NAT Gateway rather than default outbound behavior.
- NAT is associated to the Container Apps infrastructure subnet in this feature scope.

Destination scope examples:
- Public Microsoft control-plane/service endpoints required by platform components.
- External package/image sources required during runtime operations where applicable.

Troubleshooting NAT egress:

```bash
az network nat gateway show -g "$(terraform output -raw resource_group_name)" -n "$(terraform state show azurerm_nat_gateway.workload | awk '/name\s+=/{print $3}' | tr -d '"')"
az network vnet subnet show -g "$(terraform output -raw resource_group_name)" --vnet-name "$(terraform state show azurerm_virtual_network.core | awk '/name\s+=/{print $3}' | tr -d '"')" --name snet-containerapps-infra --query natGateway.id -o tsv
```

If the subnet `natGateway.id` is empty, re-apply Terraform and verify `azurerm_subnet_nat_gateway_association.container_apps_infra` exists in state.
