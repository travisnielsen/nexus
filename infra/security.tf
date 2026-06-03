# Baseline NAT Gateway for explicit outbound egress.
resource "azurerm_nat_gateway" "workload" {
  name                = "${local.identifier}-nat"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  sku_name            = "Standard"
  tags                = local.tags
}

resource "azurerm_nat_gateway_public_ip_association" "workload" {
  nat_gateway_id       = azurerm_nat_gateway.workload.id
  public_ip_address_id = azurerm_public_ip.nat_gateway.id
}

# Grant API identity access to ACR
resource "azurerm_role_assignment" "api_acr_pull" {
  scope                = module.container_registry.resource_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity access to AI Foundry account (for agent operations)
resource "azurerm_role_assignment" "api_ai_foundry_developer_containerapp" {
  scope                = module.ai_foundry.ai_foundry_id
  role_definition_name = "Azure AI Developer"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity Cognitive Services User role (for AIServices/agents data actions)
resource "azurerm_role_assignment" "api_cognitive_services_user" {
  scope                = module.ai_foundry.ai_foundry_id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity access to AI Foundry project
resource "azurerm_role_assignment" "api_ai_foundry_project" {
  scope                = module.ai_foundry.ai_foundry_project_id["nexus"]
  role_definition_name = "Azure AI Developer"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity access to Storage
resource "azurerm_role_assignment" "api_storage" {
  scope                = module.ai_storage.resource_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity access to Cosmos DB
resource "azurerm_role_assignment" "api_cosmos" {
  scope                = module.ai_cosmosdb.resource_id
  role_definition_name = "Cosmos DB Account Reader Role"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity control-plane permission required for
# create-if-not-exists bootstrap of SQL databases/containers.
resource "azurerm_role_assignment" "api_cosmos_operator" {
  scope                = module.ai_cosmosdb.resource_id
  role_definition_name = "Cosmos DB Operator"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity data-plane permission for session metadata item CRUD.
resource "azurerm_cosmosdb_sql_role_assignment" "api_identity" {
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
  # Built-in Data Contributor role: 00000000-0000-0000-0000-000000000002
  role_definition_id = "${module.ai_cosmosdb.resource_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id       = azurerm_user_assigned_identity.api_identity.principal_id
  scope              = module.ai_cosmosdb.resource_id
}

# Grant GitHub Actions service principal ACR Push access
resource "azurerm_role_assignment" "gha_acr_push" {
  scope                = module.container_registry.resource_id
  role_definition_name = "AcrPush"
  principal_id         = var.github_actions_principal_id
}

# Grant GitHub Actions service principal Contributor access at the resource group level
resource "azurerm_role_assignment" "gha_contributor" {
  scope                = azurerm_resource_group.shared_rg.id
  role_definition_name = "Contributor"
  principal_id         = var.github_actions_principal_id
}

# Cosmos DB Data Contributor role assignment for current user
resource "azurerm_cosmosdb_sql_role_assignment" "current_user" {
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
  # Built-in Data Contributor role: 00000000-0000-0000-0000-000000000002
  role_definition_id = "${module.ai_cosmosdb.resource_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id       = data.azurerm_client_config.current.object_id
  scope              = module.ai_cosmosdb.resource_id
}

# Cosmos DB Data Contributor role assignment for the Foundry project managed identity
resource "azurerm_cosmosdb_sql_role_assignment" "foundry_project" {
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
  # Built-in Data Contributor role: 00000000-0000-0000-0000-000000000002
  role_definition_id = "${module.ai_cosmosdb.resource_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id       = module.ai_foundry.ai_foundry_project_system_identity_principal_id["nexus"]
  scope              = module.ai_cosmosdb.resource_id
}

# AI Search RBAC for the Foundry project managed identity is created by the AVM
# ai_foundry module when ai_projects.<project>.create_project_connections = true.
# Required roles at AI Search scope:
# - Search Index Data Contributor
# - Search Service Contributor
#
# Keep these AVM-managed to stay out-of-the-box and avoid duplicate assignment
# conflicts (same principal + role + scope) during terraform apply.
