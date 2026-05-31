---
agent: speckit.plan
---

When the feature or implementation scope involves Terraform, you MUST delegate Terraform research and module selection to the `Azure AVM Terraform mode` agent.

Terraform detection signals include terms such as `terraform`, `.tf`, `AVM`, `Azure Verified Modules`, `azurerm`, `infra`, `state`, `plan/apply`, or Terraform file reorganization.

If Terraform is in scope:
- Invoke `Azure AVM Terraform mode` and request AVM-aligned recommendations for module selection, version pinning, variable/output structure, validation, and migration risks.
- Incorporate the returned AVM guidance into the plan output with a dedicated section named `Terraform AVM Guidance`.

If Terraform is not in scope, do not invoke `Azure AVM Terraform mode`.
