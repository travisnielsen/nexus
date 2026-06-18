#################################################################################
# Storage Account for Microsoft Foundry blob uploads and NL2SQL data
#################################################################################

module "ai_storage" {
  source                        = "Azure/avm-res-storage-storageaccount/azurerm"
  version                       = "~> 0.7.1"
  name                          = replace("${local.identifier}foundry", "-", "")
  parent_id                     = azurerm_resource_group.shared_rg.id
  location                      = var.region_aifoundry
  account_tier                  = "Standard"
  account_replication_type      = "LRS"
  public_network_access_enabled = false
  shared_access_key_enabled     = false
  private_endpoints = {
    blob = {
      subnet_resource_id            = azurerm_subnet.private_endpoints.id
      subresource_name              = "blob"
      private_dns_zone_resource_ids = toset([azurerm_private_dns_zone.storage_blob.id])
    }
  }
  tags = local.tags

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
  source                        = "Azure/avm-res-documentdb-databaseaccount/azurerm"
  version                       = "~> 0.10.0"
  name                          = "${local.identifier}-foundry"
  resource_group_name           = azurerm_resource_group.shared_rg.name
  location                      = var.region_aifoundry
  public_network_access_enabled = false
  automatic_failover_enabled    = true

  geo_locations = [
    {
      location          = var.region_aifoundry
      failover_priority = 0
      zone_redundant    = false
    }
  ]

  private_endpoints = {
    sql = {
      subnet_resource_id            = azurerm_subnet.private_endpoints.id
      subresource_name              = "SQL"
      private_dns_zone_resource_ids = toset([azurerm_private_dns_zone.cosmos_sql.id])
    }
  }

  diagnostic_settings = {
    to_law = {
      name                  = "to-law"
      workspace_resource_id = module.log_analytics.resource_id
      metric_categories     = ["SLI", "Requests"]
    }
  }

  tags = local.tags
}

resource "azurerm_cosmosdb_sql_database" "session_metadata" {
  name                = var.session_metadata_cosmos_database
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
}

resource "azurerm_cosmosdb_sql_container" "session_metadata" {
  name                  = var.session_metadata_cosmos_container
  resource_group_name   = azurerm_resource_group.shared_rg.name
  account_name          = module.ai_cosmosdb.name
  database_name         = azurerm_cosmosdb_sql_database.session_metadata.name
  partition_key_paths   = [var.session_metadata_cosmos_partition_key_path]
  partition_key_version = 1
}

# Cosmos DB database and container for Logistics API feedback records (spec 005).
# Provisioned by Terraform; API validates existence at startup via bootstrap probe.
resource "azurerm_cosmosdb_sql_database" "feedback" {
  name                = var.feedback_cosmos_database
  resource_group_name = azurerm_resource_group.shared_rg.name
  account_name        = module.ai_cosmosdb.name
}

resource "azurerm_cosmosdb_sql_container" "feedback_records" {
  name                  = var.feedback_cosmos_container
  resource_group_name   = azurerm_resource_group.shared_rg.name
  account_name          = module.ai_cosmosdb.name
  database_name         = azurerm_cosmosdb_sql_database.feedback.name
  partition_key_paths   = [var.feedback_cosmos_partition_key_path]
  partition_key_version = 1
}