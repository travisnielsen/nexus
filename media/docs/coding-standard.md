# Coding Standards

This document describes the coding standards and conventions for the Nexus project.

## Anti-Slop: Preventing Low-Quality AI-Generated Code

AI coding assistants produce useful output — but also predictable failure modes. These rules catch the most common issues automatically.

### Tooling

| Tool             | Purpose              | Command                                   |
| ---------------- | -------------------- | ----------------------------------------- |
| **ruff**         | Linting + formatting | `uv run poe lint` / `uv run poe format`  |
| **basedpyright** | Type checking        | `uv run poe typecheck`                   |
| **gitleaks**     | Secret scanning      | Pre-commit hook                           |

**Run all checks:** `uv run poe check` (per project) or `uv run --project . poe check` (monorepo)

### 1. Pydantic Models for All I/O

Never work with raw dictionaries, JSON, or untyped data. Always define a Pydantic model and validate **immediately** at the boundary:

```python
# ❌ BAD: Raw dict from API/file (AI slop)
async def process_data(data: dict) -> None:
    name = data["name"]  # Could fail, no validation
    value = data.get("value", 0)  # Type is Any

# ✅ GOOD: Pydantic model + immediate validation
from pydantic import BaseModel, Field

class FlightData(BaseModel):
    name: str = Field(min_length=1)
    value: float = Field(ge=0)

async def process_data(data: dict) -> None:
    flight = FlightData.model_validate(data)  # Fails fast with clear errors
```

This applies to:

- API request/response payloads
- Configuration files and environment variables
- Data from external services (MCP, A2A)
- Anything crossing a boundary

### 2. No Boolean Traps (FBT rule)

```python
# ❌ BAD: What does True mean here?
process_flight(flight, True, False)

# ✅ GOOD: Use keyword arguments or enums
process_flight(flight, include_historical=True, force_refresh=False)
```

### 3. No Bare Excepts (BLE rule)

```python
# ❌ BAD: Swallows everything including KeyboardInterrupt
try:
    result = await fetch_data()
except:
    pass

# ✅ GOOD: Catch specific exceptions
try:
    result = await fetch_data()
except httpx.HTTPError as e:
    logger.error("Failed to fetch data: %s", e)
    raise
```

### 4. Keep Functions Simple (C90/PLR rules)

- **Max cyclomatic complexity**: 10
- **Max nesting depth**: 3
- **Max arguments**: 7

If a function exceeds these limits, break it into smaller functions.

### 5. No Commented-Out Code (ERA rule)

```python
# ❌ BAD: Dead code cluttering the file
# old_result = process_legacy(data)
# if old_result:
#     return old_result
result = process_current(data)

# ✅ GOOD: Remove dead code, use git history if needed
result = process_current(data)
```

### 6. Security Checks (S rules)

The `S` (bandit) rules catch common security issues:

```python
# ❌ BAD: Hardcoded secrets
API_KEY = "sk-1234567890"  # S105: Hardcoded password

# ❌ BAD: SQL injection risk
query = f"SELECT * FROM flights WHERE id = {flight_id}"  # S608

# ✅ GOOD: Use environment variables and parameterized queries
API_KEY = os.environ["API_KEY"]
query = "SELECT * FROM flights WHERE id = ?"
cursor.execute(query, (flight_id,))
```

### Quality Commands

```bash
# Per project (from src/backend/api, src/backend/mcp, or src/backend/agent-a2a)
uv run poe check       # Lint + typecheck
uv run poe format      # Format + auto-fix
uv run poe lint        # Lint only
uv run poe typecheck   # Type checking only

# Monorepo (from repo root)
uv run --project . poe check    # All backend projects
uv run --project . poe format   # All backend projects
```

---

## Code Style and Formatting

### Python

- **Formatter**: ruff (line length 100, target Python 3.12+)
- **Type checker**: basedpyright in standard mode
- **Docstrings**: Google style
- All functions must have type annotations for parameters and return values
- Use `from __future__ import annotations` for forward references
- Use `logging` module (not print statements)
- Use `async/await` for I/O operations

### TypeScript / React

- **Linter**: ESLint
- Use functional components with hooks
- Define interfaces for all data structures
- Use `"use client"` directive for client components
- Prefer named exports over default exports for components
- Use Tailwind CSS for styling

---

## Asynchronous Programming

All I/O-bound operations must be asynchronous:

```python
# ❌ BAD: Blocking call in async context
import requests
response = requests.get(url)

# ✅ GOOD: Use async-compatible libraries
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

## Import Pattern

Each backend project is self-contained. Use direct imports within the project:

```python
# From src/backend/api/
from agents.tools.filter_tools import filter_flights
from agents.utils.mcp_client import MCPClient
from middleware.auth import AzureADAuthMiddleware
```

## Documentation

We follow the [Google Docstring](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#383-functions-and-methods) style guide:

```python
async def create_agent(name: str, tools: list[Tool]) -> Agent:
    """Create a new agent with the specified configuration.

    Args:
        name: The name of the agent.
        tools: The tools available to the agent.

    Returns:
        A configured agent instance.

    Raises:
        ValueError: If the name is empty.
    """
    ...
```

## Performance Considerations

- **Cache expensive computations**: Don't recalculate on every call
- **Prefer attribute access over isinstance()**: Faster in hot paths
- **Avoid redundant serialization**: Compute once, reuse

## See Also

- [Dev Setup](dev-setup.md) — Environment setup and tooling
- [Contributing](../../CONTRIBUTING.md) — Git conventions, PR guidelines
