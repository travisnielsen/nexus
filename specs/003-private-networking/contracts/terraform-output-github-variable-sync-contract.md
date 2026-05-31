# Contract: Terraform Output to GitHub Variable Synchronization

## Scope
- Sync script behavior equivalent to Cadence `update-github-vars-from-terraform.sh`.
- GitHub repository variable set required by deployment workflows.

## Inputs
- Terraform output JSON (`terraform output -json`)
- Repository identifier and authenticated GitHub CLI/API context
- Mapping definition of output keys to GitHub variable names

## Output Guarantees
1. Idempotency
- Re-running with unchanged Terraform state MUST produce no unintended modifications.

1. Diff reporting
- Script MUST report keys added, changed, unchanged, and missing required mappings.

1. Foundry migration coverage
- Sync mapping MUST include logistics deployment variables impacted by Foundry client migration.

1. Failure semantics
- Missing required mappings or failed updates MUST return non-zero exit status.

1. Dry-run mode
- Script SHOULD support dry-run to preview updates without mutation.

## Verification
- Test with known output fixture and expected variable map.
- Validate resulting GitHub variable set matches required deployment workflow inputs.
- Confirm release-prep run requires zero manual variable edits.
