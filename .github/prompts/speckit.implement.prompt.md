---
agent: speckit.implement
---

When implementing Terraform-related tasks, you MUST delegate Terraform-specific implementation guidance to `Azure AVM Terraform mode`.

If Terraform is in scope:
- Apply AVM-first patterns for module usage and version pinning.
- Execute Terraform quality checks (`terraform fmt` and `terraform validate`) before considering implementation complete.
- Where applicable in this repository, also run AVM-required checks referenced by the AVM agent instructions.

If Terraform is not in scope, do not invoke `Azure AVM Terraform mode`.
