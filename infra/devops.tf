#################################################################################
# Container Registry
#################################################################################

module "container_registry" {
  source                        = "Azure/avm-res-containerregistry-registry/azurerm"
  version                       = "~> 0.5.1"
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
