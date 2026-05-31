terraform {
  backend "azurerm" {
    resource_group_name = "rg-terraform-state"
    container_name      = "tfstate"
    key                 = "nexus.terraform.tfstate"
    use_azuread_auth    = true
  }

  required_version = ">= 1.12, < 2.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.38"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.8"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
    external = {
      source  = "hashicorp/external"
      version = "~> 2.3"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id     = var.subscription_id
  storage_use_azuread = true
}

provider "azapi" {
  subscription_id = var.subscription_id
}