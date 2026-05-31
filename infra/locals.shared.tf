# Shared naming, tagging, and operator-context locals used across domains.
locals {
  identifier = "${random_string.alpha_prefix.result}${random_string.naming.result}"

  vnet_address_space = ["10.42.0.0/16"]
  subnet_prefixes = {
    container_apps_infra = "10.42.0.0/23"
    private_endpoints    = "10.42.10.0/24"
    foundry_injection    = "10.42.20.0/24"
    utility              = "10.42.30.0/24"
  }

  tags = {
    Environment     = "Demo"
    Owner           = lookup(data.external.me.result, "name")
    SecurityControl = "Ignore"
    ManagedBy       = "Terraform"
  }

  deployer_ip = chomp(data.http.deployer_ip.response_body)
}
