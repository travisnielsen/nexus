#################################################################################
# AI Foundry (Pattern Module)
#################################################################################

module "ai_search" {
  source  = "Azure/avm-res-search-searchservice/azurerm"
  version = "~> 0.2.0"

  name                          = "${local.identifier}-ais"
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = var.region_aifoundry
  sku                           = "basic"
  public_network_access_enabled = false

  private_endpoints = {
    search = {
      subnet_resource_id            = azurerm_subnet.private_endpoints.id
      private_dns_zone_resource_ids = toset([azurerm_private_dns_zone.search.id])
    }
  }

  diagnostic_settings = {
    to_law = {
      name                  = "to-law"
      workspace_resource_id = module.log_analytics.resource_id
      metric_categories     = ["AllMetrics"]
    }
  }

  tags = local.tags
}

module "ai_foundry" {
  source  = "Azure/avm-ptn-aiml-ai-foundry/azurerm"
  version = "~> 0.11.0"

  base_name                  = local.identifier
  location                   = var.region_aifoundry
  resource_group_resource_id = azurerm_resource_group.shared_rg.id

  create_private_endpoints            = true
  private_endpoint_subnet_resource_id = azurerm_subnet.private_endpoints.id

  tags = local.tags

  # Use existing BYOR resources and let the module wire project connections.
  create_byor = false

  # AI Foundry configuration - enable agent service for thread storage in Cosmos DB
  ai_foundry = {
    create_ai_agent_service = true
    private_dns_zone_resource_ids = [
      azurerm_private_dns_zone.foundry.id,
      azurerm_private_dns_zone.foundry_cognitiveservices.id,
      azurerm_private_dns_zone.foundry_openai.id,
    ]
    network_injections = [
      {
        scenario                   = "agent"
        subnetArmId                = azurerm_subnet.foundry_injection.id
        useMicrosoftManagedNetwork = false
      }
    ]
  }

  # AI Projects configuration
  ai_projects = {
    nexus = {
      name                       = "nexus"
      display_name               = "nexus"
      description                = "AG-UI powered agentic dashboard based on Microsoft Foundry and CopilotKit"
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
    module.ai_search,
    module.ai_storage,
    module.ai_cosmosdb,
    azurerm_private_dns_zone_virtual_network_link.search,
    azurerm_private_dns_zone_virtual_network_link.foundry
  ]
}


#################################################################################
# AI Model Deployments
# Created as separate resources with explicit depends_on to avoid concurrency
# issues with Azure AI Services API. This allows running terraform apply
# without the -parallelism=1 flag.
#################################################################################

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

