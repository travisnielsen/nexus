# Create an Entra ID application registration for the MCP Server
# and configure the exposed API scope for secure access.
#
# Usage:
#   ./create-mcp-app.ps1
#   ./create-mcp-app.ps1 -authorizedClientIds <client-id>
#   ./create-mcp-app.ps1 -authorizedClientIds <client-id-1>,<client-id-2>
#   ./create-mcp-app.ps1 -authorizedClientIds @("id1", "id2", "id3")
#   ./create-mcp-app.ps1 -requireAssignment $true -authorizedUserIds @("user-object-id")
#
# Parameters:
#   -appName: Display name for the app registration (default: "Logistics-MCP-Server")
#   -authorizedClientIds: (Optional) Array of Client IDs or Object IDs to grant access to the API scope
#                         Note: Azure CLI (04b07795-8ddb-461a-bbee-02f9e1bf7b46) is always included automatically
#   -scopeName: Name of the API scope to expose (default: "Flights.Read")
#   -requireAssignment: Whether users must be explicitly assigned to access the API (default: false)
#                       false = Any user in the tenant can acquire tokens (easier for dev)
#                       true = Only assigned users/groups can acquire tokens (more secure)
#   -authorizedUserIds: (Optional) Array of user Object IDs to assign to the app (only used when requireAssignment is true)

param (
    [string]$appName = "nexus-mcp-server",
    [string[]]$authorizedClientIds = @(),
    [string]$scopeName = "Flights.Read",
    [bool]$requireAssignment = $false,
    [string[]]$authorizedUserIds = @()
)

# Well-known Azure CLI App ID - always pre-authorize for developer convenience
$azureCliAppId = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"

# Merge Azure CLI with any user-provided client IDs (avoid duplicates)
$allClientIds = @($azureCliAppId) + $authorizedClientIds | Select-Object -Unique

Write-Host "Creating MCP Server App Registration..." -ForegroundColor Cyan
Write-Host "App Name: $appName"
Write-Host "Authorized Clients: $($allClientIds.Count) client(s) (includes Azure CLI)"
foreach ($clientId in $allClientIds) {
    if ($clientId -eq $azureCliAppId) {
        Write-Host "  - $clientId (Azure CLI - auto-included)"
    } else {
        Write-Host "  - $clientId"
    }
}
Write-Host "Scope Name: $scopeName"
Write-Host "Require Assignment: $requireAssignment"
if ($requireAssignment -and $authorizedUserIds.Count -gt 0) {
    Write-Host "Authorized Users: $($authorizedUserIds.Count) user(s)"
}
Write-Host ""

# Create the application
$app = az ad app create `
    --display-name $appName `
    --sign-in-audience AzureADMyOrg `
    --query "{appId: appId, objectId: id}" `
    --output json | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to create application" -ForegroundColor Red
    exit 1
}

Write-Host "Created application with App ID: $($app.appId)" -ForegroundColor Green
Write-Host "Object ID: $($app.objectId)"

# Set the Application ID URI (required before exposing scopes)
$appIdUri = "api://$($app.appId)"
Write-Host ""
Write-Host "Setting Application ID URI to: $appIdUri" -ForegroundColor Cyan

az ad app update `
    --id $app.appId `
    --identifier-uris $appIdUri

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Failed to set Application ID URI. You may need to set it manually in the portal." -ForegroundColor Yellow
}

# Verify the identifier URI was set
$appDetails = az ad app show --id $app.appId --query "identifierUris" --output json | ConvertFrom-Json
Write-Host "Application ID URIs: $($appDetails -join ', ')"

# Generate a unique GUID for the scope
$scopeId = [guid]::NewGuid().ToString()

# Create the oauth2PermissionScopes configuration
# This exposes an API scope that other applications can request
$scopeDescription = "Allows the application to read flight data from the MCP server"
$apiConfigJson = @"
{"oauth2PermissionScopes":[{"id":"$scopeId","adminConsentDescription":"$scopeDescription","adminConsentDisplayName":"Read Flight Data","userConsentDescription":"$scopeDescription","userConsentDisplayName":"Read Flight Data","isEnabled":true,"type":"Admin","value":"$scopeName"}]}
"@

Write-Host ""
Write-Host "Exposing API scope: $scopeName (ID: $scopeId)" -ForegroundColor Cyan
az ad app update --id $app.appId --set "api=$apiConfigJson"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to expose API scope" -ForegroundColor Red
    exit 1
}

# Resolve and pre-authorize client applications (always includes Azure CLI)
$authorizedClients = @()
Write-Host ""
Write-Host "Resolving authorized client applications..." -ForegroundColor Cyan

$preAuthorizedApps = @()

foreach ($clientId in $allClientIds) {
    $clientApp = az ad app show --id $clientId --query "{appId: appId, objectId: id, displayName: displayName}" --output json 2>$null | ConvertFrom-Json

    if ($LASTEXITCODE -ne 0 -or $null -eq $clientApp) {
        Write-Host "Warning: Could not find application with ID: $clientId - skipping" -ForegroundColor Yellow
        continue
    }

    Write-Host "  Found: $($clientApp.displayName) ($($clientApp.appId))" -ForegroundColor Green
    $authorizedClients += $clientApp
    $preAuthorizedApps += @{
        appId = $clientApp.appId
        delegatedPermissionIds = @($scopeId)
    }
}

if ($preAuthorizedApps.Count -gt 0) {
    # Build the pre-authorized applications JSON
    $preAuthArray = $preAuthorizedApps | ForEach-Object {
        "{`"appId`":`"$($_.appId)`",`"delegatedPermissionIds`":[`"$scopeId`"]}"
    }
    $preAuthorizedAppJson = "{`"preAuthorizedApplications`":[$($preAuthArray -join ',')]}"

    Write-Host ""
    Write-Host "Pre-authorizing $($preAuthorizedApps.Count) client application(s) to access the API scope..." -ForegroundColor Cyan
    az ad app update --id $app.appId --set "api=$preAuthorizedAppJson"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Failed to pre-authorize client applications. You may need to configure this manually." -ForegroundColor Yellow
    } else {
        Write-Host "Successfully pre-authorized $($preAuthorizedApps.Count) client(s)" -ForegroundColor Green
    }
} else {
    Write-Host "Warning: No valid client applications found to pre-authorize" -ForegroundColor Yellow
}

# Create a service principal for the application (required for token validation)
Write-Host ""
Write-Host "Creating service principal..." -ForegroundColor Cyan
$sp = az ad sp create --id $app.appId --query "{appId: appId, objectId: id}" --output json 2>$null | ConvertFrom-Json

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Service principal may already exist or could not be created." -ForegroundColor Yellow
    # Try to get existing service principal
    $sp = az ad sp show --id $app.appId --query "{appId: appId, objectId: id}" --output json 2>$null | ConvertFrom-Json
} else {
    Write-Host "Created service principal with Object ID: $($sp.objectId)" -ForegroundColor Green
}

# Configure user assignment requirement on the Enterprise Application (Service Principal)
Write-Host ""
if ($requireAssignment) {
    Write-Host "Configuring: User assignment REQUIRED (only assigned users can access)" -ForegroundColor Cyan
    az ad sp update --id $sp.objectId --set "appRoleAssignmentRequired=true" 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Failed to set assignment requirement. Configure manually in Enterprise Applications." -ForegroundColor Yellow
    } else {
        Write-Host "Set 'Assignment required' = Yes" -ForegroundColor Green
    }
    
    # Assign users if provided
    if ($authorizedUserIds.Count -gt 0) {
        Write-Host ""
        Write-Host "Assigning users to the application..." -ForegroundColor Cyan
        
        # Get the default app role ID (00000000-0000-0000-0000-000000000000 for default access)
        $defaultRoleId = "00000000-0000-0000-0000-000000000000"
        
        foreach ($userId in $authorizedUserIds) {
            Write-Host "  Assigning user: $userId"
            
            # Create app role assignment
            $assignmentResult = az rest --method POST `
                --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$($sp.objectId)/appRoleAssignedTo" `
                --headers "Content-Type=application/json" `
                --body "{`"principalId`":`"$userId`",`"resourceId`":`"$($sp.objectId)`",`"appRoleId`":`"$defaultRoleId`"}" 2>$null
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "    Warning: Failed to assign user $userId" -ForegroundColor Yellow
            } else {
                Write-Host "    Assigned successfully" -ForegroundColor Green
            }
        }
    } else {
        Write-Host ""
        Write-Host "No users specified for assignment. Add users manually or use -authorizedUserIds parameter." -ForegroundColor Yellow
        Write-Host "  To get your user Object ID: az ad signed-in-user show --query id -o tsv" -ForegroundColor Gray
    }
} else {
    Write-Host "Configuring: User assignment NOT required (any tenant user can access)" -ForegroundColor Cyan
    az ad sp update --id $sp.objectId --set "appRoleAssignmentRequired=false" 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Failed to set assignment requirement. This is usually the default." -ForegroundColor Yellow
    } else {
        Write-Host "Set 'Assignment required' = No" -ForegroundColor Green
    }
}

# Get tenant ID
$tenantId = az account show --query tenantId --output tsv

# Output summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "MCP Server App Registration Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application Details:" -ForegroundColor Cyan
Write-Host "  Display Name:      $appName"
Write-Host "  App (Client) ID:   $($app.appId)"
Write-Host "  Object ID:         $($app.objectId)"
Write-Host "  Tenant ID:         $tenantId"
Write-Host ""
Write-Host "API Configuration:" -ForegroundColor Cyan
Write-Host "  App ID URI:        $appIdUri"
Write-Host "  Scope Name:        $scopeName"
Write-Host "  Scope ID:          $scopeId"
Write-Host "  Full Scope:        $appIdUri/$scopeName"
Write-Host ""
Write-Host "Access Configuration:" -ForegroundColor Cyan
if ($requireAssignment) {
    Write-Host "  Assignment Required: Yes (only assigned users/groups can access)"
    if ($authorizedUserIds.Count -gt 0) {
        Write-Host "  Assigned Users:      $($authorizedUserIds.Count) user(s)"
    }
} else {
    Write-Host "  Assignment Required: No (any user in the tenant can access)"
}
Write-Host ""
if ($authorizedClients.Count -gt 0) {
    Write-Host "Pre-Authorized Clients:" -ForegroundColor Cyan
    foreach ($client in $authorizedClients) {
        if ($client.appId -eq $azureCliAppId) {
            Write-Host "  - $($client.displayName) ($($client.appId)) [auto-included]"
        } else {
            Write-Host "  - $($client.displayName) ($($client.appId))"
        }
    }
    Write-Host ""
} else {
    Write-Host "Pre-Authorized Clients: (none resolved)" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "Environment Variables for MCP Server:" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "AZURE_AD_TENANT_ID=$tenantId"
Write-Host "AZURE_AD_CLIENT_ID=$($app.appId)"
Write-Host "AUTH_ENABLED=true"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "Environment Variables for Backend (MCP Client):" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "MCP_CLIENT_ID=$($app.appId)"
Write-Host "MCP_AUTH_ENABLED=true"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Target Scope (for token acquisition):" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  $appIdUri/$scopeName" -ForegroundColor White
Write-Host ""
Write-Host "  Or use .default for client credentials flow:"
Write-Host "  $appIdUri/.default" -ForegroundColor White
Write-Host ""
