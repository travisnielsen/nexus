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

## Step 2: Configure Variables

Create a `terraform.tfvars` file (not committed to source control):

```hcl
subscription_id             = "<your-subscription-id>"
region                      = "westus3"
region_aifoundry            = "eastus2"
frontend_app_client_id      = "<frontend-app-registration-client-id>"
mcp_app_client_id           = "<mcp-app-registration-client-id>"
github_actions_principal_id = "<github-actions-sp-object-id>"
auth_enabled                = true  # Set to false for development
```

## Step 3: Deploy Infrastructure

```bash
# Login to Azure
az login

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply changes
terraform apply
```

## Step 4: Note Output Values

After deployment, Terraform outputs important values needed for configuration:

```bash
terraform output
```

Key outputs:
- `frontend_url` - URL for the deployed frontend
- `api_url` - URL for the deployed API
- `mcp_url` - URL for the deployed MCP server
- `appinsights_connection_string` - Connection string for telemetry

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
