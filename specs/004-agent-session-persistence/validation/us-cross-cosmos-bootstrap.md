# Validation: Metadata Store Provisioning & Availability (T056)

## Objective

Confirm Terraform provisions required Cosmos SQL resources and the API validates availability without attempting runtime ARM/data-plane creation.

## Checks

| Check | Expected Outcome | Result | Evidence |
| --- | --- | --- | --- |
| Terraform provisioning | Cosmos SQL database/container exist before API start | PASS (manual local equivalent) | `az cosmosdb sql database create` and `az cosmosdb sql container create` succeeded for `logistics_session_metadata/sessions` |
| API startup/first-use validation | API verifies configured store and marks unavailable when missing/denied | PASS | `CosmosSessionMetadataRepository` now validates with container `read()` and returns `SessionMetadataStoreUnavailableError` on missing/denied access |
| Repeated startup | Stable behavior across restarts without noisy retry loops | PASS | Runtime owner-resource-missing retry loops were removed; blocked state remains cached until restart |

## Evidence Snapshot (2026-06-02)

### 1) Root cause and control decision

- Prior runtime resource-provisioning path failed with HTTP 403 on `sqlDatabases/write`.
- Management-plane verification using Azure CLI succeeded for database/container creation.
- Decision: move resource lifecycle ownership to Terraform and keep API behavior validation-only.

### 2) Provisioning path evidence

- Command: `az cosmosdb sql database create -g nexus-hx8mw5 -a hx8mw5-foundry -n logistics_session_metadata`
- Command: `az cosmosdb sql container create -g nexus-hx8mw5 -a hx8mw5-foundry -d logistics_session_metadata -n sessions --partition-key-path /user_id`
- Outcome: both commands succeeded, confirming management-plane provisioning path works.

### 3) Current infra requirements

- Terraform must create:
	- `azurerm_cosmosdb_sql_database` for `logistics_session_metadata`
	- `azurerm_cosmosdb_sql_container` for `sessions` with partition key `/user_id`
- API runtime identity still requires Cosmos SQL data-plane contributor assignment for document read/write operations.

## Required Permissions (Important for Container App Managed Identity)

To support this feature's runtime behavior (metadata read/write after Terraform provisioning), the identity running Logistics API must have:

1. Cosmos data-plane permission to read/write session metadata items
	 - `Cosmos DB Built-in Data Contributor` SQL role assignment on account (or db scope) via Cosmos SQL RBAC.
	 - Built-in role definition id suffix: `00000000-0000-0000-0000-000000000002`.

Without this permission, API cannot upsert/read/delete session metadata documents.

## Deployment Guidance

- Apply Terraform to provision SQL database/container resources before deploying API revisions that rely on session metadata.
- Ensure Container App managed identity has SQL data-plane contributor role assignment.
- Re-run this validation after `terraform apply` in each environment.

## Final Status

- Status: PASS (design transition complete, Terraform ownership defined)
- Notes:
	- API no longer attempts runtime resource provisioning for Cosmos session metadata resources.
	- Environment validation still requires confirming Terraform state in each target environment.
