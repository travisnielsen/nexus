---
agent: speckit.tasks
---

When the scenario includes Terraform work, you MUST use outputs from `Azure AVM Terraform mode` to generate tasks.

If Terraform is in scope:
- Ensure task lists include AVM module selection, version pinning, variable/output alignment, and Terraform validation steps.
- Include explicit tasks for `terraform fmt`, `terraform validate`, and any AVM-required verification steps relevant to the repository.
- Mark Terraform tasks so they are clearly distinguishable from non-Terraform tasks.

If Terraform is not in scope, proceed without invoking `Azure AVM Terraform mode`.
