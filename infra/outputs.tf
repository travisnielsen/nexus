# ==============================================================
# General Outputs
# ==============================================================

output "azure_tenant_id" {
  description = "Azure tenant ID"
  value       = data.azurerm_client_config.current.tenant_id
}

output "azure_subscription_id" {
  description = "Azure subscription ID"
  value       = data.azurerm_subscription.current.subscription_id
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.shared_rg.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.shared_rg.location
}

# ==============================================================
# Observability Outputs
# ==============================================================

output "appinsights_connection_string" {
  description = "Application Insights connection string"
  value       = module.application_insights.connection_string
  sensitive   = true
}

output "appinsights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = module.application_insights.instrumentation_key
  sensitive   = true
}

# ==============================================================
# AI Foundry Outputs
# ==============================================================

output "ai_foundry_id" {
  description = "AI Foundry account resource ID"
  value       = module.ai_foundry.ai_foundry_id
}

output "ai_foundry_project_id" {
  description = "AI Foundry project resource ID"
  value       = module.ai_foundry.ai_foundry_project_id
}

output "cosmos_db_id" {
  description = "Cosmos DB account resource ID"
  value       = module.ai_foundry.cosmos_db_id
}

output "key_vault_id" {
  description = "Key Vault resource ID"
  value       = module.ai_foundry.key_vault_id
}

output "storage_account_id" {
  description = "Storage account resource ID"
  value       = module.ai_foundry.storage_account_id
}

# ==============================================================
# Container App Outputs
# ==============================================================

output "container_app_url" {
  description = "Container App API URL"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "container_app_identity_client_id" {
  description = "Container App managed identity client ID"
  value       = azurerm_user_assigned_identity.api_identity.client_id
}

output "container_registry_login_server" {
  description = "Container Registry login server"
  value       = module.container_registry.resource.login_server
}

output "container_registry_name" {
  description = "Container Registry resource name"
  value       = module.container_registry.resource.name
}

# ==============================================================
# Service Endpoint Outputs
# ==============================================================

output "frontend_url" {
  description = "Container App URL for Next.js frontend"
  value       = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "logistics_url" {
  description = "Container App URL for backend API"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "logistics_mcp_url" {
  description = "Container App URL for MCP server"
  value       = "https://${azurerm_container_app.mcp.ingress[0].fqdn}"
}

output "recommendations_url" {
  description = "Internal URL for the A2A recommendations agent"
  value       = "https://${azurerm_container_app.a2a.ingress[0].fqdn}"
}

output "logistics_container_app_name" {
  description = "Container App name for backend API"
  value       = azurerm_container_app.api.name
}

output "frontend_container_app_name" {
  description = "Container App name for frontend"
  value       = azurerm_container_app.frontend.name
}

output "logistics_mcp_container_app_name" {
  description = "Container App name for MCP service"
  value       = azurerm_container_app.mcp.name
}

output "recommendations_container_app_name" {
  description = "Container App name for recommendations service"
  value       = azurerm_container_app.a2a.name
}

output "foundry_project_endpoint" {
  description = "Foundry project endpoint used by backend services"
  value       = local.ai_project_endpoint
}

output "frontend_app_client_id" {
  description = "Frontend app registration client ID used by frontend build-time auth config"
  value       = var.frontend_app_client_id
}

output "backend_api_scope_uri" {
  description = "Fully qualified backend API scope URI used by backend and frontend auth config"
  value       = var.backend_api_scope_uri
}

output "auth_enabled" {
  description = "Whether auth is enabled for runtime services"
  value       = var.auth_enabled
}

# ==============================================================
# GitHub Actions Deployment Variables (mapped to script expectations)
# ==============================================================

output "api_container_app_name" {
  description = "Container App name for backend API (GitHub Actions mapping)"
  value       = azurerm_container_app.api.name
}

output "mcp_container_app_name" {
  description = "Container App name for MCP service (GitHub Actions mapping)"
  value       = azurerm_container_app.mcp.name
}

output "a2a_container_app_name" {
  description = "Container App name for A2A recommendations service (GitHub Actions mapping)"
  value       = azurerm_container_app.a2a.name
}

output "api_url" {
  description = "Backend API URL (GitHub Actions mapping)"
  value       = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}
