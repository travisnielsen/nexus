resource "azurerm_virtual_network" "core" {
  name                = "${local.identifier}-vnet"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  address_space       = local.vnet_address_space
  tags                = local.tags
}

resource "azurerm_subnet" "container_apps_infra" {
  name                 = "snet-containerapps-infra"
  resource_group_name  = azurerm_resource_group.shared_rg.name
  virtual_network_name = azurerm_virtual_network.core.name
  address_prefixes     = [local.subnet_prefixes.container_apps_infra]

  delegation {
    name = "aca-delegation"
    service_delegation {
      name = "Microsoft.App/environments"
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  name                              = "snet-private-endpoints"
  resource_group_name               = azurerm_resource_group.shared_rg.name
  virtual_network_name              = azurerm_virtual_network.core.name
  address_prefixes                  = [local.subnet_prefixes.private_endpoints]
  private_endpoint_network_policies = "Disabled"
}

resource "azurerm_subnet" "foundry_injection" {
  name                 = "snet-foundry-injection"
  resource_group_name  = azurerm_resource_group.shared_rg.name
  virtual_network_name = azurerm_virtual_network.core.name
  address_prefixes     = [local.subnet_prefixes.foundry_injection]
}

resource "azurerm_subnet" "utility" {
  name                 = "snet-utility"
  resource_group_name  = azurerm_resource_group.shared_rg.name
  virtual_network_name = azurerm_virtual_network.core.name
  address_prefixes     = [local.subnet_prefixes.utility]
}

resource "azurerm_private_dns_zone" "cosmos_sql" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = azurerm_resource_group.shared_rg.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos_sql" {
  name                  = "${local.identifier}-cosmos-link"
  private_dns_zone_name = azurerm_private_dns_zone.cosmos_sql.name
  resource_group_name   = azurerm_resource_group.shared_rg.name
  virtual_network_id    = azurerm_virtual_network.core.id
  registration_enabled  = false
  tags                  = local.tags
}

resource "azurerm_private_dns_zone" "foundry" {
  name                = "privatelink.services.ai.azure.com"
  resource_group_name = azurerm_resource_group.shared_rg.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone" "search" {
  name                = "privatelink.search.windows.net"
  resource_group_name = azurerm_resource_group.shared_rg.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "foundry" {
  name                  = "${local.identifier}-foundry-link"
  private_dns_zone_name = azurerm_private_dns_zone.foundry.name
  resource_group_name   = azurerm_resource_group.shared_rg.name
  virtual_network_id    = azurerm_virtual_network.core.id
  registration_enabled  = false
  tags                  = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "search" {
  name                  = "${local.identifier}-search-link"
  private_dns_zone_name = azurerm_private_dns_zone.search.name
  resource_group_name   = azurerm_resource_group.shared_rg.name
  virtual_network_id    = azurerm_virtual_network.core.id
  registration_enabled  = false
  tags                  = local.tags
}

# Public IP used by the shared NAT Gateway egress baseline.
resource "azurerm_public_ip" "nat_gateway" {
  name                = "${local.identifier}-nat-pip"
  resource_group_name = azurerm_resource_group.shared_rg.name
  location            = azurerm_resource_group.shared_rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_subnet_nat_gateway_association" "container_apps_infra" {
  subnet_id      = azurerm_subnet.container_apps_infra.id
  nat_gateway_id = azurerm_nat_gateway.workload.id
}
