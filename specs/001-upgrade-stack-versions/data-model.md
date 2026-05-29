# Data Model: Repository Stable Version Upgrade

## Entity: UpgradeScope

- Description: The bounded set of code areas included in this feature.
- Fields:
  - `id` (string): Stable identifier (e.g., `backend-api`, `frontend-app`).
  - `path` (string): Repository path in scope.
  - `ecosystem` (enum): `python` | `node`.
  - `owner` (string): Responsible maintainer/team.
- Relationships:
  - One `UpgradeScope` has many `DependencyVersionRecord`.
  - One `UpgradeScope` has many `ValidationResult`.

## Entity: DependencyVersionRecord

- Description: Version transition for each direct dependency in scope.
- Fields:
  - `scope_id` (string, FK -> UpgradeScope).
  - `name` (string).
  - `from_version` (string).
  - `to_version` (string).
  - `disposition` (enum): `upgraded` | `replaced`.
  - `is_foundry_client_related` (boolean).
- Validation rules:
  - `to_version` MUST be stable release or approved stable replacement package.
  - `disposition=upgraded` requires `to_version` set.

## Entity: DependencyReplacementRecord

- Description: Captures replacements/forks for unsupported dependencies.
- Fields:
  - `scope_id` (string, FK -> UpgradeScope).
  - `original_dependency` (string).
  - `replacement_type` (enum): `stable_substitute` | `in_repo_fork`.
  - `replacement_reference` (string).
  - `maintenance_owner` (string).
  - `equivalence_notes` (string).
  - `validation_evidence_ref` (string).
- Validation rules:
  - `replacement_type=in_repo_fork` requires `maintenance_owner`.

## Entity: LockfileUpdateRecord

- Description: Records transitive update effects from lockfile regeneration.
- Fields:
  - `scope_id` (string, FK -> UpgradeScope).
  - `lockfile_path` (string).
  - `regenerated` (boolean).
  - `transitive_changes_count` (integer).
  - `conflict_resolution_notes` (string).
- Validation rules:
  - If dependency graph changes, `regenerated` MUST be true.

## Entity: ValidationResult

- Description: Output of quality and regression checks per scope.
- Fields:
  - `scope_id` (string, FK -> UpgradeScope).
  - `check_name` (string).
  - `category` (enum): `lint` | `typecheck` | `unit` | `integration` | `protocol` | `smoke`.
  - `status` (enum): `pass` | `fail`.
  - `is_critical_regression_gate` (boolean).
  - `run_reference` (string).
- Validation rules:
  - All `is_critical_regression_gate=true` records MUST be `pass` before release.

## State Transitions

1. `identified` -> `upgraded` for direct dependencies with stable compatible release.
2. `identified` -> `replaced` for unsupported/no-compatible dependencies.
3. `pending_validation` -> `validated` after all required checks pass.
4. Feature release gate unlocks only when critical regression checks are 100% pass.
