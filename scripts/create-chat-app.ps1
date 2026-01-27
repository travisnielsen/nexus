# Create an Entra ID application for the client app (React / Next.js)
# and configure necessary API permissions.
param (
    [string]$appName = "nexus-dashboard",
    [string]$redirectUri = "http://localhost:3000"
)
# Create the application
$app = az ad app create `
    --display-name $appName `
    --query "{appId: appId, objectId: id}" `
    --output json | ConvertFrom-Json
Write-Host "Created application with App ID: $($app.appId)"

# set the redirect URI for SPA platform
$spaConfig = @{
    redirectUris = @($redirectUri)
} | ConvertTo-Json -Compress

az ad app update `
    --id $app.appId `
    --set "spa=$spaConfig"

# Add API permissions (e.g., User.Read from Microsoft Graph)
# Permission ID e1fe6dd8-ba31-4d61-89e7-88639da4683d is "User.Read" delegated permission
az ad app permission add `
    --id $app.appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Expose an API scope for the backend
# First, set the Application ID URI (required before exposing scopes)
Write-Host "Setting Application ID URI to: api://$($app.appId)"
az ad app update `
    --id $app.appId `
    --identifier-uris "api://$($app.appId)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Failed to set Application ID URI. You may need to set it manually in the portal."
}

# Verify the identifier URI was set
$appDetails = az ad app show --id $app.appId --query "identifierUris" --output json | ConvertFrom-Json
Write-Host "Application ID URIs: $($appDetails -join ', ')"

# Generate a unique GUID for the scope
$scopeId = [guid]::NewGuid().ToString()

# Create the oauth2PermissionScopes configuration as a JSON string
# Note: Azure CLI requires the JSON to be properly escaped
$apiConfigJson = @"
{"oauth2PermissionScopes":[{"id":"$scopeId","adminConsentDescription":"Allow the application to access the API on behalf of the signed-in user","adminConsentDisplayName":"Access API as user","userConsentDescription":"Allow the application to access the API on your behalf","userConsentDisplayName":"Access API as user","isEnabled":true,"type":"User","value":"access_as_user"}]}
"@

Write-Host "Exposing API scope with ID: $scopeId"
az ad app update --id $app.appId --set "api=$apiConfigJson"

# Verify the scope was created
Write-Host "Verifying API configuration..."
az ad app show --id $app.appId --query "api" --output json

Write-Host "Application setup complete. Details:"
Write-Host "App ID: $($app.appId)"
Write-Host "Object ID: $($app.objectId)"
Write-Host "Tenant ID: $(az account show --query tenantId --output tsv)"
Write-Host "Redirect URI: $redirectUri"
Write-Host "Scope ID: "api://$($app.appId)/access_as_user""
Write-Host "Please configure your frontend application with the above App ID and Redirect URI."
