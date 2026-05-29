# Release Gate Checklist: Repository Stable Version Upgrade

Created: 2026-05-29
Feature: `specs/001-upgrade-stack-versions/spec.md`

## Required Gates

- [ ] All scoped direct dependencies upgraded or replaced with supported alternatives.
- [ ] Lockfiles regenerated where dependency graph changed.
- [ ] Critical regression scenarios: 100% pass.
- [ ] MCP-mediated data path verified for operational dashboard flow.
- [ ] Typed service boundary contracts validated.
- [ ] Frontend lint/build pass.
- [ ] Monorepo backend quality checks pass (`uv run --project . poe check`).
- [ ] Foundry-native client migration complete and validated.
- [ ] Final upgrade summary and release decision artifacts complete.
