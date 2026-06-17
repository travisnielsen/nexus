#################################################################################
# Container App Environment for Backend API
#################################################################################

module "container_app_environment" {
  source  = "Azure/avm-res-app-managedenvironment/azurerm"
  version = "~> 0.5.0"

  name                = "${local.identifier}-cae"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  log_analytics_workspace = {
    resource_id = module.log_analytics.resource_id
  }
  zone_redundant = false
  vnet_configuration = {
    infrastructure_subnet_id = azurerm_subnet.container_apps_infra.id
    internal                 = false
  }
  workload_profiles = [
    {
      name                  = "Consumption"
      workload_profile_type = "Consumption"
    }
  ]
  tags = local.tags
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
  # Normalize endpoint domain to services.ai so private DNS/PE routing is used.
  ai_hub_endpoint_raw = trimsuffix(data.azapi_resource.ai_foundry_hub.output.properties.endpoint, "/")
  ai_hub_endpoint     = replace(local.ai_hub_endpoint_raw, ".cognitiveservices.azure.com", ".services.ai.azure.com")
  ai_project_name     = module.ai_foundry.ai_foundry_project_name["nexus"]
  ai_project_endpoint = "${local.ai_hub_endpoint}/api/projects/${local.ai_project_name}"
}

resource "azurerm_user_assigned_identity" "api_identity" {
  name                = "${local.identifier}-api-identity"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  tags                = local.tags
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
      image  = "mcr.microsoft.com/k8se/quickstart:latest" # Placeholder; replaced by CI/CD
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
        value = var.backend_api_app_client_id
      }
      env {
        name  = "AZURE_AD_API_SCOPE_URI"
        value = var.backend_api_scope_uri
      }
      env {
        name  = "FOUNDRY_PROJECT_ENDPOINT"
        value = local.ai_project_endpoint
      }
      env {
        name  = "FOUNDRY_MODEL"
        value = "gpt-5.2-chat"
      }
      env {
        name  = "FOUNDRY_EMBEDDING_MODEL"
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
        name  = "AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"
        value = "false"
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
      env {
        name  = "SESSION_METADATA_COSMOS_DB_ENDPOINT"
        value = "https://${module.ai_cosmosdb.name}.documents.azure.com:443/"
      }
      env {
        name  = "SESSION_METADATA_COSMOS_DATABASE"
        value = var.session_metadata_cosmos_database
      }
      env {
        name  = "SESSION_METADATA_COSMOS_CONTAINER"
        value = var.session_metadata_cosmos_container
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull,
    azurerm_role_assignment.api_ai_foundry_developer_containerapp,
    azurerm_role_assignment.api_storage,
    azurerm_cosmosdb_sql_database.session_metadata,
    azurerm_cosmosdb_sql_container.session_metadata,
    azurerm_container_app.mcp,
    azurerm_container_app.a2a
  ]

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]
  }
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
      image  = "mcr.microsoft.com/k8se/quickstart:latest" # Placeholder; replaced by CI/CD
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

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]
  }
}

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
    external_enabled = false
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
      image  = "mcr.microsoft.com/k8se/quickstart:latest" # Placeholder; replaced by CI/CD
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

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]
  }
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
      image  = "mcr.microsoft.com/k8se/quickstart:latest" # Placeholder; replaced by CI/CD
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "FOUNDRY_PROJECT_ENDPOINT"
        value = local.ai_project_endpoint
      }

      env {
        name  = "FOUNDRY_MODEL"
        value = "gpt-5.2-chat"
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.api_acr_pull
  ]

  lifecycle {
    ignore_changes = [
      template[0].container[0].image
    ]
  }
}
