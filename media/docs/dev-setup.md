# Dev Setup

## System Requirements

| Tool        | Version | Purpose                       |
| ----------- | ------- | ----------------------------- |
| **Python**  | 3.12+   | Backend services              |
| **Node.js** | 20+     | Frontend build and dev server |
| **uv**      | latest  | Python package management     |
| **npm**     | latest  | Frontend package management   |

## Quick Setup

From the repository root:

```bash
./devsetup.sh
```

This script:

- Validates prerequisites (`uv`, optional Node.js)
- Installs Python runtimes (`3.11`, `3.12`, `3.13`) via `uv`
- Syncs backend dependencies for `api`, `mcp`, and `agent-a2a` with `uv sync --dev`
- Installs frontend dependencies in `src/frontend` via `npm install`
- Configures git hooks in `.githooks/`

Optional — pass a Python version label for display:

```bash
./devsetup.sh 3.12
```

## Manual Setup

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Backend Dependencies

Each backend project has its own `pyproject.toml`:

```bash
cd src/backend/api && uv sync --dev
cd src/backend/mcp && uv sync --dev
cd src/backend/agent-a2a && uv sync --dev
```

Or use the monorepo Poe tasks from the repo root:

```bash
uv run --project . poe setup-api
uv run --project . poe setup-mcp
uv run --project . poe setup-a2a
```

### Install Frontend Dependencies

```bash
cd src/frontend && npm install
```

## Running the Application

Start all services from the repository root:

```bash
npm run dev
```

This starts four concurrent processes with colored output:

| Label     | Service              | URL                    |
| --------- | -------------------- | ---------------------- |
| **[ui]**  | Next.js frontend     | http://localhost:3000   |
| **[mcp]** | MCP server (DuckDB)  | http://localhost:8001   |
| **[a2a]** | A2A recommendations  | http://localhost:5002   |
| **[api]** | Backend API (MAF)    | http://localhost:8000   |

Or start services individually:

```bash
# Frontend
cd src/frontend && npm run dev:ui

# Backend API
cd src/backend/api && uv run uvicorn main:app --port 8000 --reload

# MCP Server
cd src/backend/mcp && uv run uvicorn main:rest_app --port 8001 --reload

# A2A Agent
cd src/backend/agent-a2a && uv run uvicorn main:app --port 5002 --reload
```

## VS Code Setup

Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and open the workspace file (`nexus.code-workspace`).

Each backend project has a `pyrightconfig.json` for type checking.

### Copilot Auto-Approve Commands

| Pattern              | Commands                              | Purpose         |
| -------------------- | ------------------------------------- | --------------- |
| `/^uv run poe\b/`   | `uv run poe check`, `uv run poe lint`| Poe task runner |
| `/^uv sync\b/`      | `uv sync`                            | Dependency sync |
| `/^git status\b/`    | `git status`                          | Read-only git   |
| `/^git diff\b/`      | `git diff`                            | Read-only git   |
| `/^git log\b/`       | `git log`                             | Read-only git   |
| `/^npm run\b/`       | `npm run dev`, `npm run lint`         | npm scripts     |

## Available Poe Tasks

Poe tasks are defined in `pyproject.toml` at the repo root and in each backend project.

### Monorepo Root (`uv run --project . poe <task>`)

| Task             | Description                                  |
| ---------------- | -------------------------------------------- |
| `bootstrap`      | Run `devsetup.sh`                            |
| `setup-api`      | Install API dependencies                     |
| `setup-mcp`      | Install MCP dependencies                     |
| `setup-a2a`      | Install A2A dependencies                     |
| `setup-frontend` | Install frontend dependencies                |
| `check`          | Run all backend checks (api + mcp + a2a)     |
| `format`         | Format all backend code (api + mcp + a2a)    |

### Per-Project (`cd src/backend/<project> && uv run poe <task>`)

| Task        | Description                             |
| ----------- | --------------------------------------- |
| `format`    | Format code with ruff                   |
| `lint`      | Lint code with ruff                     |
| `typecheck` | Type-check with basedpyright            |
| `check`     | Run lint + typecheck                    |
| `dev`       | Start the service in development mode   |

## Environment Variables

See [Getting Started](getting-started.md) for the full list of environment variables and how to configure `.env` files for each service.

## See Also

- [Getting Started](getting-started.md) — Prerequisites, configuration, first run
- [Coding Standard](coding-standard.md) — Code style and conventions
- [Contributing](../../CONTRIBUTING.md) — Git conventions, PR guidelines
- [Glossary](glossary.md) — Abbreviations and terms
