#################################################################################
# Observability Services
#################################################################################

# Log Analytics Workspace (shared)
module "log_analytics" {
  source                                             = "Azure/avm-res-operationalinsights-workspace/azurerm"
  version                                            = "~> 0.5.1"
  name                                               = "${local.identifier}-law"
  resource_group_name                                = azurerm_resource_group.shared_rg.name
  location                                           = azurerm_resource_group.shared_rg.location
  log_analytics_workspace_internet_ingestion_enabled = true
  log_analytics_workspace_internet_query_enabled     = true
  tags                                               = local.tags
}

# Application Insights
module "application_insights" {
  source              = "Azure/avm-res-insights-component/azurerm"
  version             = "~> 0.4.0"
  name                = "${local.identifier}-appi"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  workspace_id        = module.log_analytics.resource_id
  application_type    = "web"
  tags                = local.tags
}
