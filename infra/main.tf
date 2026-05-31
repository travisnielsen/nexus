# main.tf - compatibility bootstrap for shared foundation resources

# Data sources
data "azurerm_client_config" "current" {}
data "azurerm_subscription" "current" {}

data "external" "me" {
  program = ["az", "account", "show", "--query", "user"]
}

# Get the public IP of the machine running Terraform
data "http" "deployer_ip" {
  url = "https://api.ipify.org"
}

# Random naming
resource "random_string" "naming" {
  special = false
  upper   = false
  length  = 5
}

resource "random_string" "alpha_prefix" {
  special = false
  upper   = false
  length  = 1
  lower   = true
  numeric = false
}

# Resource Group
resource "azurerm_resource_group" "shared_rg" {
  name     = "nexus-${local.identifier}"
  location = var.region
  tags     = local.tags
}