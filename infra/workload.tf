#################################################################################
# Deployer IP Address
#################################################################################

# Get the public IP of the machine running Terraform
data "http" "deployer_ip" {
  url = "https://api.ipify.org"
}

locals {
  deployer_ip = chomp(data.http.deployer_ip.response_body)
}


#################################################################################
# Observability Services
#################################################################################

# Log Analytics Workspace (shared)
module "log_analytics" {
  source  = "Azure/avm-res-operationalinsights-workspace/azurerm"
  name                            = "${local.identifier}-law"
  resource_group_name             = azurerm_resource_group.shared_rg.name
  location                        = azurerm_resource_group.shared_rg.location
  log_analytics_workspace_internet_ingestion_enabled = true
  log_analytics_workspace_internet_query_enabled     = true
  tags                            = local.tags
}

# Application Insights
module "application_insights" {
  source  = "Azure/avm-res-insights-component/azurerm"
  name                = "${local.identifier}-appi"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  workspace_id        = module.log_analytics.resource_id
  application_type    = "web"
  tags                = local.tags
}


#################################################################################
# Container Registry
#################################################################################

module "container_registry" {
  source  = "Azure/avm-res-containerregistry-registry/azurerm"
  name                          = replace("${local.identifier}acr", "-", "")
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = azurerm_resource_group.shared_rg.location
  sku                           = "Standard"
  zone_redundancy_enabled       = false
  public_network_access_enabled = true
  admin_enabled                 = false
  tags                          = local.tags

  diagnostic_settings = {
    to_law = {
      name                  = "to-law"
      workspace_resource_id = module.log_analytics.resource_id
    }
  }
}


#################################################################################
# Storage Account for Microsoft Foundry blob uploads and NL2SQL data
#################################################################################

module "ai_storage" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  name                          = replace("${local.identifier}foundry", "-", "")
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = var.region_aifoundry
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = false
  tags                          = local.tags

  # Enable static website hosting for frontend
  static_website = {
    frontend = {
      index_document     = "index.html"
      error_404_document = "index.html"  # SPA fallback
    }
  }

  # Allow deployer IP and Azure services through the firewall
  network_rules = {
    default_action = "Deny"
    bypass         = ["AzureServices"]
    ip_rules       = [local.deployer_ip]
  }

  # Role assignment for current user to upload blobs
  role_assignments = {
    storage_blob_contributor = {
      role_definition_id_or_name = "Storage Blob Data Contributor"
      principal_id               = data.azurerm_client_config.current.object_id
    }
  }
}


#################################################################################
# Cosmos DB Account for Microsoft Foundry agent service thread storage
#################################################################################

module "ai_cosmosdb" {
  source  = "Azure/avm-res-documentdb-databaseaccount/azurerm"
  name                          = "${local.identifier}-foundry"
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = var.region_aifoundry
  public_network_access_enabled = true
  analytical_storage_enabled    = true
  automatic_failover_enabled    = true
  
  geo_locations = [
    {
      location          = var.region_aifoundry
      failover_priority = 0
      zone_redundant    = false
    }
  ]

  diagnostic_settings = {
    to_law = {
      name                  = "to-law"
      workspace_resource_id = module.log_analytics.resource_id
      metric_categories = ["SLI", "Requests"]
    }
  }

  tags = local.tags
}

# Cosmos DB Data Contributor role assignment for current user
resource "azurerm_cosmosdb_sql_role_assignment" "current_user" {
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
  # Built-in Data Contributor role: 00000000-0000-0000-0000-000000000002
  role_definition_id  = "${module.ai_cosmosdb.resource_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = data.azurerm_client_config.current.object_id
  scope               = module.ai_cosmosdb.resource_id
}

# Cosmos DB Data Contributor role assignment for the Foundry project managed identity
resource "azurerm_cosmosdb_sql_role_assignment" "foundry_project" {
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
  # Built-in Data Contributor role: 00000000-0000-0000-0000-000000000002
  role_definition_id  = "${module.ai_cosmosdb.resource_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = module.ai_foundry.ai_foundry_project_system_identity_principal_id["dataagent"]
  scope               = module.ai_cosmosdb.resource_id
}


#################################################################################
# AI Search - linked to Microsoft Foundry
#################################################################################

module "ai_search" {
  source  = "Azure/avm-res-search-searchservice/azurerm"
  name                          = "${local.identifier}"
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = var.region_aifoundry
  sku                           = "standard"
  public_network_access_enabled = true
  local_authentication_enabled  = true
  # Enable both API key and AAD authentication
  authentication_failure_mode   = "http401WithBearerChallenge"
  tags                          = local.tags

  # Enable managed identity for RBAC access to storage and AI services
  managed_identities = {
    system_assigned = true
  }

  # Role assignment for current user to manage search service
  role_assignments = {
    search_service_contributor = {
      role_definition_id_or_name = "Search Service Contributor"
      principal_id               = data.azurerm_client_config.current.object_id
    }
    search_index_data_reader = {
      role_definition_id_or_name = "Search Index Data Reader"
      principal_id               = data.azurerm_client_config.current.object_id
    }
  }

  diagnostic_settings = {
    to_law = {
      name                  = "to-law"
      workspace_resource_id = module.log_analytics.resource_id
    }
  }
}


#################################################################################
# AI Foundry (Pattern Module)
#################################################################################

module "ai_foundry" {
  source  = "Azure/avm-ptn-aiml-ai-foundry/azurerm"
  version = "~> 0.8.0"

  base_name                  = local.identifier
  location                   = var.region_aifoundry
  resource_group_resource_id = azurerm_resource_group.shared_rg.id

  tags = local.tags

  # Disable BYOR creation - using existing resources via project connections only
  # Note: The *_definition blocks have bugs in AVM 0.8.0, so we skip them
  create_byor = false

  # AI Foundry configuration - enable agent service for thread storage in Cosmos DB
  ai_foundry = {
    create_ai_agent_service = true
  }

  # AI Projects configuration
  ai_projects = {
    dataagent = {
      name                       = "ag-ui-demo"
      display_name               = "AG-UI Samples"
      description                = "Data exploration agents and related resources"
      create_project_connections = true
      cosmos_db_connection = {
        existing_resource_id = module.ai_cosmosdb.resource_id
      }
      storage_account_connection = {
        existing_resource_id = module.ai_storage.resource_id
      }
      ai_search_connection = {
        existing_resource_id = module.ai_search.resource_id
      }
    }
  }

  # Model deployments are created separately below to avoid concurrency issues
  # with Azure AI Services API (see azapi_resource.ai_model_deployment_* resources)

  depends_on = [
    module.ai_storage,
    module.ai_cosmosdb
  ]
}


#################################################################################
# AI Model Deployments
# Created as separate resources with explicit depends_on to avoid concurrency
# issues with Azure AI Services API. This allows running terraform apply
# without the -parallelism=1 flag.
#################################################################################

resource "azapi_resource" "ai_model_deployment_gpt5" {
  name      = "gpt-5-chat"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-5-chat"
        version = "2025-10-03"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
  }
  schema_validation_enabled = false

  depends_on = [module.ai_foundry]
}

resource "azapi_resource" "ai_model_deployment_gpt52" {
  name      = "gpt-5.2-chat"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-5.2-chat"
        version = "2025-12-11"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
  }
  schema_validation_enabled = false

  # Sequential deployment to avoid Azure API concurrency issues
  depends_on = [azapi_resource.ai_model_deployment_gpt5]
}

resource "azapi_resource" "ai_model_deployment_embedding_small" {
  name      = "embedding-small"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "text-embedding-3-small"
        version = "1"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
  }
  schema_validation_enabled = false

  # Sequential deployment to avoid Azure API concurrency issues
  depends_on = [azapi_resource.ai_model_deployment_gpt52]
}

resource "azapi_resource" "ai_model_deployment_embedding_large" {
  name      = "embedding-large"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "text-embedding-3-large"
        version = "1"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 120
    }
  }
  schema_validation_enabled = false

  # Sequential deployment to avoid Azure API concurrency issues
  depends_on = [azapi_resource.ai_model_deployment_embedding_small]
}

resource "azapi_resource" "ai_model_deployment_gpt41" {
  name      = "gpt-4.1"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-4.1"
        version = "2025-04-14"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
  }
  schema_validation_enabled = false

  # Sequential deployment to avoid Azure API concurrency issues
  depends_on = [azapi_resource.ai_model_deployment_embedding_large]
}

resource "azapi_resource" "ai_model_deployment_gpt41_mini" {
  name      = "gpt-4.1-mini"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-4.1-mini"
        version = "2025-04-14"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
  }
  schema_validation_enabled = false

  # Sequential deployment to avoid Azure API concurrency issues
  depends_on = [azapi_resource.ai_model_deployment_gpt41]
}

resource "azapi_resource" "ai_model_deployment_gpt4o_mini" {
  name      = "gpt-4o-mini"
  parent_id = module.ai_foundry.ai_foundry_id
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-10-01-preview"
  body = {
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-4o-mini"
        version = "2024-07-18"
      }
      versionUpgradeOption = "OnceNewDefaultVersionAvailable"
    }
    sku = {
      name     = "GlobalStandard"
      capacity = 150
    }
  }
  schema_validation_enabled = false

  # Sequential deployment to avoid Azure API concurrency issues
  depends_on = [azapi_resource.ai_model_deployment_gpt41_mini]
}


#################################################################################
# Container App Environment for Backend API
#################################################################################

module "container_app_environment" {
  source  = "Azure/avm-res-app-managedenvironment/azurerm"
  version = "~> 0.2"

  name                           = "${local.identifier}-cae"
  resource_group_name            = azurerm_resource_group.shared_rg.name
  location                       = azurerm_resource_group.shared_rg.location
  log_analytics_workspace = {
    resource_id = module.log_analytics.resource_id
  }
  zone_redundancy_enabled        = false
  infrastructure_subnet_id       = null  # Use consumption plan without VNet integration
  internal_load_balancer_enabled = false
  tags                           = local.tags
}


#################################################################################
# Container App for Backend API
#################################################################################

# Get the AI Foundry hub properties to extract the endpoint
data "azapi_resource" "ai_foundry_hub" {
  type                   = "Microsoft.CognitiveServices/accounts@2024-10-01"
  resource_id            = module.ai_foundry.ai_foundry_id
  response_export_values = ["properties.endpoint"]
}

locals {
  # The endpoint property gives us the hub URL directly
  # Format: https://<hub-name>-<random>.services.ai.azure.com/
  ai_hub_endpoint     = data.azapi_resource.ai_foundry_hub.output.properties.endpoint
  ai_project_name     = module.ai_foundry.ai_foundry_project_name["dataagent"]
  ai_project_endpoint = "${trimsuffix(local.ai_hub_endpoint, "/")}/api/projects/${local.ai_project_name}"
}

resource "azurerm_user_assigned_identity" "api_identity" {
  name                = "${local.identifier}-api-identity"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  tags                = local.tags
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
  scope                = module.ai_foundry.ai_foundry_project_id["dataagent"]
  role_definition_name = "Azure AI Developer"
  principal_id         = azurerm_user_assigned_identity.api_identity.principal_id
}

# Grant API identity access to AI Search
resource "azurerm_role_assignment" "api_search" {
  scope                = module.ai_search.resource_id
  role_definition_name = "Search Index Data Reader"
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

resource "azurerm_container_app" "api" {
  name                         = "${local.identifier}-api"
  resource_group_name          = azurerm_resource_group.shared_rg.name
  container_app_environment_id = module.container_app_environment.resource_id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api_identity.id]
  }

  registry {
    server   = module.container_registry.resource.login_server
    identity = azurerm_user_assigned_identity.api_identity.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    cors {
      allowed_origins    = ["*"]
      allowed_methods    = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allowed_headers    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "api"
      image  = "${module.container_registry.resource.login_server}/logistics-agui:latest"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.api_identity.client_id
      }
      env {
        name  = "AZURE_AD_TENANT_ID"
        value = data.azurerm_client_config.current.tenant_id
      }
      env {
        name  = "AZURE_AD_CLIENT_ID"
        value = var.frontend_app_client_id
      }
      env {
        name  = "AZURE_AI_PROJECT_ENDPOINT"
        value = local.ai_project_endpoint
      }
      env {
        name  = "AZURE_AI_MODEL_DEPLOYMENT_NAME"
        value = "gpt-4o-mini"
      }
      env {
        name  = "AZURE_AI_EMBEDDING_DEPLOYMENT"
        value = "embedding-large"
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = module.application_insights.connection_string
      }
      env {
        name  = "ENABLE_INSTRUMENTATION"
        value = "true"
      }
      env {
        name  = "ENABLE_SENSITIVE_DATA"
        value = "true"
      }
      env {
        name  = "AUTH_ENABLED"
        value = tostring(var.auth_enabled)
      }
      env {
        name  = "MCP_SERVER_URL"
        value = "https://${azurerm_container_app.mcp.ingress[0].fqdn}"
      }
      env {
        name  = "MCP_ENABLED"
        value = "true"
      }
      env {
        name  = "MCP_AUTH_ENABLED"
        value = tostring(var.auth_enabled)
      }
      env {
        name  = "MCP_CLIENT_ID"
        value = var.mcp_app_client_id
      }
      env {
        name  = "RECOMMENDATIONS_AGENT_URL"
        value = "https://${azurerm_container_app.a2a.ingress[0].fqdn}"
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull,
    azurerm_role_assignment.api_ai_foundry_developer_containerapp,
    azurerm_role_assignment.api_search,
    azurerm_role_assignment.api_storage,
    azurerm_container_app.mcp,
    azurerm_container_app.a2a
  ]
}


#################################################################################
# Container App for Next.js Frontend
#################################################################################

resource "azurerm_container_app" "frontend" {
  name                         = "${local.identifier}-frontend"
  resource_group_name          = azurerm_resource_group.shared_rg.name
  container_app_environment_id = module.container_app_environment.resource_id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api_identity.id]
  }

  registry {
    server   = module.container_registry.resource.login_server
    identity = azurerm_user_assigned_identity.api_identity.id
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    cors {
      allowed_origins    = ["*"]
      allowed_methods    = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allowed_headers    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "frontend"
      image  = "${module.container_registry.resource.login_server}/logistics-frontend:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "NODE_ENV"
        value = "production"
      }
      env {
        name  = "AGENT_API_BASE_URL"
        value = "https://${azurerm_container_app.api.ingress[0].fqdn}"
      }
      # Note: NEXT_PUBLIC_* vars are NOT set here because they are baked into
      # the JavaScript bundle at build time (via Docker build args in GitHub Actions).
      # Setting them at runtime has no effect on Next.js client-side code.
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull,
    azurerm_container_app.api
  ]
}

#################################################################################
# Container App for MCP Server (Flight Data API)
#################################################################################

resource "azurerm_container_app" "mcp" {
  name                         = "${local.identifier}-mcp"
  resource_group_name          = azurerm_resource_group.shared_rg.name
  container_app_environment_id = module.container_app_environment.resource_id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api_identity.id]
  }

  registry {
    server   = module.container_registry.resource.login_server
    identity = azurerm_user_assigned_identity.api_identity.id
  }

  ingress {
    external_enabled = true
    target_port      = 8001
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }

    cors {
      allowed_origins    = ["*"]
      allowed_methods    = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allowed_headers    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "mcp"
      image  = "${module.container_registry.resource.login_server}/logistics-mcp:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "MCP_HOST"
        value = "0.0.0.0"
      }
      env {
        name  = "MCP_PORT"
        value = "8001"
      }
      env {
        name  = "AUTH_ENABLED"
        value = tostring(var.auth_enabled)
      }
      env {
        name  = "AZURE_AD_TENANT_ID"
        value = data.azurerm_client_config.current.tenant_id
      }
      env {
        name  = "AZURE_AD_CLIENT_ID"
        value = var.mcp_app_client_id
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull
  ]
}


#################################################################################
# Container App for A2A Recommendations Agent
#################################################################################

resource "azurerm_container_app" "a2a" {
  name                         = "${local.identifier}-a2a"
  resource_group_name          = azurerm_resource_group.shared_rg.name
  container_app_environment_id = module.container_app_environment.resource_id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api_identity.id]
  }

  registry {
    server   = module.container_registry.resource.login_server
    identity = azurerm_user_assigned_identity.api_identity.id
  }

  ingress {
    external_enabled = false
    target_port      = 5002
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "a2a"
      image  = "${module.container_registry.resource.login_server}/logistics-a2a:latest"
      cpu    = 0.5
      memory = "1Gi"
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull
  ]
}


#################################################################################
# Storage Account for Azure Dashboard (Static Website)
#################################################################################

module "dashboard_storage" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  name                          = replace("${local.identifier}dashboard", "-", "")
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = azurerm_resource_group.shared_rg.location
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = true
  shared_access_key_enabled     = true
  https_traffic_only_enabled    = true
  allow_nested_items_to_be_public = true  # Required for static website public access
  tags                          = local.tags

  # Enable static website hosting
  static_website = {
    dashboard = {
      index_document     = "index.html"
      error_404_document = "index.html"  # SPA fallback
    }
  }

  # No network rules - allow public access for static website
  # (The $web container needs to be publicly accessible)
  network_rules = {
    default_action = "Allow"
  }

  # Role assignments for blob upload access and firewall management
  role_assignments = {
    storage_blob_contributor = {
      role_definition_id_or_name = "Storage Blob Data Contributor"
      principal_id               = data.azurerm_client_config.current.object_id
    }
    github_actions_blob_contributor = {
      role_definition_id_or_name = "Storage Blob Data Contributor"
      principal_id               = var.github_actions_principal_id
    }
    github_actions_contributor = {
      role_definition_id_or_name = "Contributor"
      principal_id               = var.github_actions_principal_id
    }
  }
}


output "frontend_url" {
  value = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "api_url" {
  value = "https://${azurerm_container_app.api.ingress[0].fqdn}"
}

output "mcp_url" {
  value = "https://${azurerm_container_app.mcp.ingress[0].fqdn}"
}

output "a2a_url" {
  description = "Internal URL for the A2A recommendations agent"
  value       = "https://${azurerm_container_app.a2a.ingress[0].fqdn}"
}

output "dashboard_storage_account_name" {
  description = "Storage account name for the Azure Dashboard static website"
  value       = module.dashboard_storage.name
}

output "dashboard_url" {
  description = "URL for the Azure Dashboard static website"
  value       = module.dashboard_storage.resource.primary_web_endpoint
  sensitive   = true
}
