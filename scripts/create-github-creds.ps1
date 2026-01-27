# Parameters
param (
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$StorageAccountName,
    
    [Parameter(Mandatory=$true)]
    [string]$ContainerRegistryName
)

# Create app registration
az ad app create --display-name "github-actions-nexus"

# Get the app ID
$APP_ID = az ad app list --display-name "github-actions-nexus" --query "[0].appId" -o tsv

# Create service principal
az ad sp create --id $APP_ID

# Create federated credential for GitHub Actions
az ad app federated-credential create --id $APP_ID `
  --parameters '{
    "name": "github-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:travisnielsen/nexus:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Grant Storage Blob Data Contributor role to the storage account
az role assignment create `
  --assignee $APP_ID `
  --role "Storage Blob Data Contributor" `
  --scope "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"

# Grant Storage Account Contributor role (required to modify network rules during deployment)
az role assignment create `
  --assignee $APP_ID `
  --role "Storage Account Contributor" `
  --scope "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"

# Grant Azure Container Registry Push permission (to push images)
$ACR_ID = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.ContainerRegistry/registries/$ContainerRegistryName"
az role assignment create `
  --assignee $APP_ID `
  --role "AcrPush" `
  --scope $ACR_ID

# Grant Container Apps Contributor permission (resource group level)
az role assignment create `
  --assignee $APP_ID `
  --role "Contributor" `
  --scope "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName"