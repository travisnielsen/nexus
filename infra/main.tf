# main.tf - Modular Infrastructure Configuration

# Data sources
data "azurerm_client_config" "current" {}
data "azurerm_subscription" "current" {}

data "external" "me" {
  program = ["az", "account", "show", "--query", "user"]
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

# Local values with alphabetic prefix
locals {
  identifier = "${random_string.alpha_prefix.result}${random_string.naming.result}"
  tags = {
    Environment     = "Demo"
    Owner          = lookup(data.external.me.result, "name")
    SecurityControl = "Ignore"
    ManagedBy      = "Terraform"
  }
}

# Resource Group
resource "azurerm_resource_group" "shared_rg" {
  name     = "ag-ui-${local.identifier}"
  location = var.region
  tags     = local.tags
}