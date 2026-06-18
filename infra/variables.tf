variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID to deploy environment into."
}

variable "region" {
  type        = string
  default     = "westus3"
  description = "Azure region to deploy resources."
}

variable "region_aifoundry" {
  type        = string
  default     = "eastus2"
  description = "Azure region to deploy AI Foundry resources."
}

variable "region_alternative" {
  type        = string
  default     = "eastus"
  description = "Alternative Azure region to deploy resources."
}

variable "frontend_app_client_id" {
  type        = string
  description = "Azure AD App Registration client ID for the frontend application. Used by the API to validate authentication tokens."
}

variable "backend_api_app_client_id" {
  type        = string
  description = "Azure AD App Registration client ID for the backend API application."
}

variable "backend_api_scope_uri" {
  type        = string
  description = "Fully qualified scope URI for the backend API (for example api://<backend-app-guid>/access_as_user)."
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

variable "utility_vm_admin_password" {
  type        = string
  sensitive   = true
  description = "Administrator password for the utility Windows VM; provide this value via terraform.tfvars."
}

variable "session_metadata_cosmos_database" {
  type        = string
  default     = "logistics_session_metadata"
  description = "Cosmos SQL database name for Logistics API session metadata."
}

variable "session_metadata_cosmos_container" {
  type        = string
  default     = "sessions"
  description = "Cosmos SQL container name for Logistics API session metadata."
}

variable "session_metadata_cosmos_partition_key_path" {
  type        = string
  default     = "/user_id"
  description = "Partition key path for the session metadata Cosmos SQL container."
}

variable "feedback_cosmos_database" {
  type        = string
  default     = "logistics_feedback"
  description = "Cosmos SQL database name for Logistics API feedback records."
}

variable "feedback_cosmos_container" {
  type        = string
  default     = "feedback_records"
  description = "Cosmos SQL container name for Logistics API feedback records."
}

variable "feedback_cosmos_partition_key_path" {
  type        = string
  default     = "/user_id"
  description = "Partition key path for the feedback records Cosmos SQL container."
}
