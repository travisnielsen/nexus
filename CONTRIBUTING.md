# Contributing

## Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>
```

### Type

| Type       | Description                              |
| ---------- | ---------------------------------------- |
| `feat`     | New feature                              |
| `fix`      | Bug fix                                  |
| `docs`     | Documentation only                       |
| `style`    | Formatting, whitespace (no logic change) |
| `refactor` | Code restructure (no feature/fix)        |
| `perf`     | Performance improvement                  |
| `test`     | Add or update tests                      |
| `build`    | Build system, dependencies               |
| `ci`       | CI/CD configuration                      |
| `chore`    | Maintenance, tooling                     |
| `revert`   | Revert a previous commit                 |

### Scope (Optional)

| Scope      | Description                                        |
| ---------- | -------------------------------------------------- |
| `api`      | Backend API (FastAPI + MAF agent)                  |
| `mcp`      | MCP server (DuckDB, flight data)                   |
| `a2a`      | A2A recommendations agent                          |
| `agent`    | Agent tools, prompts, utilities                    |
| `frontend` | Next.js frontend, CopilotKit integration           |
| `infra`    | Infrastructure, Terraform                          |
| `config`   | Configuration files                                |
| `deps`     | Dependencies                                      |
| `monitor`  | Monitoring dashboards, telemetry                   |

### Subject Rules

- Use **imperative mood**: "add" not "added" or "adds"
- **Don't capitalize** the first letter
- **No period** at the end
- Keep under **50 characters**

### Examples

```
feat(agent): add historical payload tool
fix(frontend): correct filter reset on clear
docs: update getting-started guide
refactor(api): extract data helpers to utils
ci: add deploy-a2a workflow
```

## Branch Naming

```
<type>/<ticket>-<short-description>
```

Examples:

```
feat/42-chart-predictions
fix/99-filter-context-sync
docs/setup-guide
```

## Pull Requests

### Opening a PR

1. Create a feature branch from `main`
2. Make focused, atomic commits following the conventions above
3. Push your branch and open a PR against `main`
4. Fill in the PR template with a clear description

### PR Checklist

- [ ] Commits follow Conventional Commits format
- [ ] `uv run --project . poe check` passes for all affected backend projects
- [ ] `npm run lint` passes (if frontend changes)
- [ ] New code has type annotations
- [ ] Documentation updated if behavior changes

### Code Review Guidelines

- Review for correctness, clarity, and maintainability
- Check that changes match the PR description
- Test locally when reviewing non-trivial changes
- Be constructive and specific in feedback

## Git Hooks

This repo uses local git hooks in `.githooks/`, installed by `devsetup.sh`:

| Hook         | Action                                                  |
| ------------ | ------------------------------------------------------- |
| `commit-msg` | Enforces Conventional Commits format                    |
| `pre-commit` | Blocks direct commits to `main`/`master`, runs checks   |
| `pre-push`   | Runs `uv run --project . poe check` and frontend lint   |

To install manually:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

## See Also

- [Coding Standard](media/docs/coding-standard.md) — Code style and conventions
- [Dev Setup](media/docs/dev-setup.md) — Environment setup and tooling
