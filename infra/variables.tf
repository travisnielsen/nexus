variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID to deploy environment into."
}

variable "region" {
  type    = string
  default = "westus3"
  description = "Azure region to deploy resources."
}

variable "region_aifoundry" {
  type    = string
  default = "eastus2"
  description = "Azure region to deploy AI Foundry resources."
}

variable "frontend_app_client_id" {
  type        = string
  description = "Azure AD App Registration client ID for the frontend application. Used by the API to validate authentication tokens."
}

variable "auth_enabled" {
  type        = bool
  default     = true
  description = "Set to false to disable authentication on the API. WARNING: Do not use in production!"
}

variable "mcp_app_client_id" {
  type        = string
  description = "Azure AD App Registration client ID for the MCP server. Used for token validation when MCP auth is enabled."
}

variable "github_actions_principal_id" {
  type        = string
  description = "Object ID of the GitHub Actions service principal (github-actions-nexus) for RBAC assignments."
}
