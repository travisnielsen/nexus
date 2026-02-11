# GitHub Copilot Instructions

This document provides context for GitHub Copilot to understand the project structure, conventions, and architecture.

## Project Overview

This is an **Enterprise Data Agent** - an agent-assisted logistics dashboard for monitoring flight shipment capacity and utilization. It combines:

- **Microsoft Agent Framework (MAF)** for agent orchestration
- **CopilotKit** for the conversational UI experience
- **AG-UI protocol** for agent-frontend communication
- **A2A protocol** for agent-to-agent communication
- **MCP (Model Context Protocol)** for data access via DuckDB

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend (Next.js)                         │
│                   CopilotKit React Components                        │
│                         Port: 3000                                   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ AG-UI Protocol (SSE)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + MAF)                         │
│                   Logistics Agent + Tools                            │
│                         Port: 8000                                   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTP (REST)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Server (Starlette)                        │
│                   Flight Data (DuckDB + REST)                        │
│                         Port: 8001                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/
├── frontend/               # Next.js 16 + React 19 + CopilotKit
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   │   ├── page.tsx   # Main dashboard page
│   │   │   └── api/copilotkit/route.ts  # CopilotKit runtime proxy
│   │   ├── components/    # React components
│   │   └── lib/           # Types, hooks, utilities
│   └── package.json
│
├── backend/                # All backend services
│   ├── api/               # FastAPI + Microsoft Agent Framework (main API)
│   │   ├── main.py            # FastAPI app, REST endpoints, agent setup
│   │   ├── clients.py         # Chat client factory (Responses API)
│   │   ├── monitoring.py      # OpenTelemetry observability setup
│   │   ├── Dockerfile         # Production Dockerfile (for ACR/Azure deployment)
│   │   ├── Dockerfile.local   # Local dev Dockerfile (includes Azure CLI)
│   │   ├── patches/           # Context sync & telemetry patches (must import first)
│   │   │   ├── __init__.py        # Patch config and apply_all_patches()
│   │   │   ├── agui_event_stream.py # AG-UI context sync (threadId, activeFilter, OTel)
│   │   │   └── conversation_id_injection.py # Telemetry conversation ID patches
│   │   ├── agents/
│   │   │   ├── logistics_agent.py  # Agent configuration and state schema
│   │   │   ├── prompts/       # System prompt templates
│   │   │   │   └── logistics_agent.md  # Agent system prompt (loaded at runtime)
│   │   │   ├── tools/         # Agent tool implementations (LLM-callable)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── filter_tools.py        # Dashboard filter tools (filter_flights, reset_filters)
│   │   │   │   ├── analysis_tools.py      # Flight analysis tools (analyze_flights)
│   │   │   │   ├── chart_tools.py         # Historical/predicted data tools
│   │   │   │   └── recommendation_tools.py # A2A recommendations tool (get_recommendations)
│   │   │   └── utils/         # Utility modules (not LLM-callable)
│   │   │       ├── __init__.py
│   │   │       ├── mcp_client.py      # HTTP client for MCP server
│   │   │       └── data_helpers.py    # Shared data access functions
│   │   ├── middleware/        # Auth and thread management
│   │   │   ├── auth.py        # Azure AD authentication
│   │   │   └── responses_api.py   # Responses API thread middleware
│   │   └── pyproject.toml     # Python dependencies (uv)
│   │
│   ├── mcp/                # MCP Server (Model Context Protocol)
│   │   ├── main.py            # Starlette app with DuckDB + SSE transport
│   │   ├── auth.py            # Entra ID authentication for MCP
│   │   ├── data/              # Flight data JSON files (source of truth)
│   │   │   ├── flights.json   # Flight and historical data
│   │   │   ├── oneview.json   # OneView integration data
│   │   │   └── utilization.json # Utilization schema
│   │   └── pyproject.toml
│   │
│   └── agent-a2a/          # A2A Recommendations Agent
│       ├── main.py            # A2A FastAPI application
│       └── pyproject.toml
│
├── monitoring/             # Observability and tracing tools
│   ├── azure-dashboard/   # Vite + React app for viewing App Insights traces
│   │   ├── src/           # React components and MSAL auth
│   │   ├── package.json   # Vite, React 18, MSAL, Tailwind
│   │   └── vite.config.ts
│   └── otel-dashboard/    # Local OpenTelemetry stack (Grafana Tempo)
│       ├── docker-compose.yml
│       └── grafana/       # Grafana dashboards
│
├── infra/                 # Terraform infrastructure (Azure)
│   ├── main.tf            # Resource group and data sources
│   ├── workload.tf        # All Azure resources (Container Apps, Storage, AI Foundry)
│   ├── variables.tf       # Input variables
│   ├── outputs.tf         # Output values
│   └── terraform.tfvars   # Variable values (not committed)
│
├── .github/
│   ├── workflows/         # GitHub Actions CI/CD
│   │   ├── deploy-api.yml      # Deploy backend API to Container Apps
│   │   ├── deploy-frontend.yml # Deploy Next.js frontend to Container Apps
│   │   ├── deploy-mcp.yml      # Deploy MCP server to Container Apps
│   │   └── deploy-dashboard.yml # Deploy azure-dashboard to Storage static website
│   └── copilot-instructions.md  # This file
│
└── scripts/               # Setup and run scripts
```

## Technology Stack

### Frontend
- **Next.js 16** with App Router and Turbopack
- **React 19** with hooks
- **TypeScript 5**
- **Tailwind CSS 4**
- **CopilotKit 1.51** for conversational UI
- **AG-UI Client** (`@ag-ui/client@0.0.42`) for agent communication (version pinned via npm overrides)
- **MSAL v5** (`@azure/msal-browser@5.1.0`, `@azure/msal-react@5.0.3`) for Azure AD authentication

### Backend
- **Python 3.12+** with `uv` package manager
- **FastAPI** for REST API and SSE endpoints
- **Microsoft Agent Framework (MAF)** for agent orchestration:
  - `agent-framework-core` - Core agent functionality
  - `agent-framework-ag-ui` - AG-UI protocol support
  - `agent-framework-azure-ai` - Azure AI Foundry integration
  - `agent-framework-a2a` - A2A protocol support
- **Azure AI Foundry** for LLM (GPT-4o)
- **Azure AD** authentication (optional)
- **OpenTelemetry** for observability

### MCP Server
- **FastMCP** with Starlette for HTTP/SSE transport
- **DuckDB** for SQL query capabilities on JSON data
- Exposes REST API, MCP tools, and MCP resources

### A2A Agent
- **a2a-sdk** for A2A protocol support
- Recommendations generation agent

## Key Patterns and Conventions

### Agent Tools

Agent tools are defined in `backend/api/agents/tools/`. Each tool:
1. Uses the `@ai_function` decorator from MAF with `name` and `description`
2. Uses `Annotated` type hints with `Field` for parameter descriptions
3. Returns structured dict data for UI state updates

Current tools in `logistics_agent.py`:

| Tool | Purpose |
|------|---------|
| `filter_flights` | Filter dashboard by route, utilization, risk (additive filtering) |
| `reset_filters` | Clear all filters and show all flights |
| `analyze_flights` | Answer questions about displayed data (reads filter from ContextVar) |
| `get_recommendations` | Get AI-powered recommendations via A2A agent |
| `get_historical_payload` | Get historical payload data for charts |
| `get_predicted_payload` | Get predicted payload data for charts |

**System Prompt**: Loaded from `backend/api/agents/prompts/logistics_agent.md` at runtime.

Example tool pattern:
```python
from agent_framework import ai_function
from pydantic import Field
from typing import Annotated

@ai_function(
    name="my_tool",
    description="Description for the LLM to understand when to use this tool.",
)
def my_tool(
    param: Annotated[str, Field(description="Parameter description")],
) -> dict:
    """Implementation docstring."""
    return {"result": data}
```

### State Management

The frontend maintains local display state and syncs filter context to the backend:
- `displayFlights` - Local state for flight data (fetched via REST API)
- `displayHistorical` - Local state for chart data
- `displayFilter` - Current filter criteria (tracked locally, exposed via `useCopilotReadable`)

**Note**: This app does NOT use `predict_state_config`. The frontend fetches data via REST API when tools complete, using `useRenderToolCall` to observe tool execution. This avoids race conditions from state sync loops.

### Data Access

All flight data flows through the MCP server (source of truth):
1. **MCP Server** (`backend/mcp/`) - Hosts all data with DuckDB for SQL queries
2. **MCP Client** (`backend/api/agents/utils/mcp_client.py`) - HTTP client using `httpx`
3. **Data Helpers** (`backend/api/agents/utils/data_helpers.py`) - Shared data access for agent tools
4. **Backend REST API** - Proxies MCP data to frontend

The MCP server provides:
- REST endpoints: `/api/flights`, `/api/flights/{id}`, `/api/summary`, `/api/historical`, `/api/predictions`, `/api/routes`
- MCP SSE endpoint: `/sse` (for MCP protocol)
- MCP tools: `get_tables`, `query_data`

**Note**: The backend has NO local data files. All data comes from MCP.

### Filter Architecture

Filters use an additive pattern with context synchronization:
1. Frontend sends current filter state via `useCopilotReadable` as context
2. Backend patches sync this to `current_active_filter` ContextVar (in `agui_event_stream.py`)
3. `filter_flights` merges new filters with existing (additive)
4. `reset_filters` clears all filters and the ContextVar
5. Frontend's `useRenderToolCall` triggers REST fetch when tool starts
6. `analyze_flights` auto-reads filter from ContextVar - does not require LLM to pass filter params

### Authentication

Authentication uses Azure AD (Entra ID):
- Frontend: MSAL React with `@azure/msal-browser`
- Backend: `fastapi-azure-auth` middleware
- MCP: Optional Entra ID auth via `backend/mcp/auth.py`
- Can be disabled with `AUTH_ENABLED=false` for development

### Environment Variables

Backend API (`.env` in `/backend/api`):
```env
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_AD_CLIENT_ID=...
AZURE_AD_TENANT_ID=...
AUTH_ENABLED=false  # Development only (default: true)
MCP_SERVER_URL=http://localhost:8001
RECOMMENDATIONS_AGENT_URL=http://localhost:5002
AGENT_FRAMEWORK_LOG_LEVEL=WARNING  # DEBUG for verbose logging

# Telemetry
ENABLE_INSTRUMENTATION=true
APPLICATIONINSIGHTS_CONNECTION_STRING=...  # Azure Monitor
ENABLE_SENSITIVE_DATA=true  # Log prompts/responses (dev only)
# OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317  # Alternative: Aspire/Tempo
```

Frontend (`.env.local` in `/frontend`):
```env
NEXT_PUBLIC_AZURE_AD_CLIENT_ID=...
NEXT_PUBLIC_AZURE_AD_TENANT_ID=...
NEXT_PUBLIC_AUTH_ENABLED=false  # Development only (default: true)
```

## Common Tasks

### Adding a New Agent Tool

1. Create or update a file in `backend/api/agents/tools/` (naming convention: `*_tools.py`)
2. Define the tool function with `@ai_function` decorator (with `name` and `description`)
3. Use `Annotated[type, Field(description="...")]` for parameters
4. Export from `backend/api/agents/tools/__init__.py`
5. Import in `backend/api/agents/logistics_agent.py`
6. Add to the agent's tool list in `create_logistics_agent()`

**Note**: Utility functions that are NOT LLM-callable should go in `backend/api/agents/utils/` instead.

### Adding a New Frontend Action

Frontend actions allow the LLM to update UI state:

```typescript
useCopilotAction({
  name: "myAction",
  parameters: [{
    name: "param",
    description: "Parameter description",
    required: true,
  }],
  handler({ param }) {
    // Update React state
  },
});
```

### Running the Application

```bash
# Install dependencies
npm install

# Start all services (frontend + backend + MCP + A2A)
npm run dev
```

This starts four concurrent processes with colored output:
- **[ui]** Next.js frontend on http://localhost:3000
- **[mcp]** MCP server on http://localhost:8001
- **[a2a]** A2A agent on http://localhost:5002
- **[api]** Backend API on http://localhost:8000

```bash
# Or run with Docker Compose
# Note: --env-file is required to bake NEXT_PUBLIC_* vars into the frontend build
docker compose --env-file frontend/.env.local up --build

# Or start individually:
# Frontend: cd frontend && npm run dev:ui
# Backend API: cd backend/api && uv run uvicorn main:app --port 8000 --reload
# MCP: cd backend/mcp && uv run uvicorn main:rest_app --port 8001 --reload
# A2A: cd backend/agent-a2a && uv run uvicorn main:app --port 5002 --reload
```

### Docker Development

The project includes Docker Compose for local development:

- **`docker-compose.yml`** - Orchestrates all 4 services (mcp, agent-a2a, backend, frontend)
- **`Dockerfile.local`** - Backend with Azure CLI for credential pass-through
- **`Dockerfile`** - Production build (no Azure CLI, uses Managed Identity)
- **`.dockerignore`** - Each backend project has a `.dockerignore` to exclude local `.venv` directories

**Important**: Docker Compose mounts `~/.azure` from the host to enable `AzureCliCredential` in containers.

**Building with environment variables**:
Next.js requires `NEXT_PUBLIC_*` variables at build time (they're baked into the client bundle):
```bash
# Always use --env-file for Docker builds
docker compose --env-file frontend/.env.local up --build
```
If you skip `--env-file`, authentication will fail because the frontend uses placeholder values.

## Azure Infrastructure

The project deploys to Azure using Terraform (`infra/`). All resources are created in a single resource group.

### Azure Resources

| Resource | Purpose |
|----------|---------|
| **Container Apps Environment** | Hosts backend, frontend, and MCP containers |
| **Container App (API)** | Backend FastAPI + MAF agent (port 8000) |
| **Container App (Frontend)** | Next.js dashboard (port 3000) |
| **Container App (MCP)** | MCP server with DuckDB (port 8001) |
| **Container Registry** | Stores Docker images for all services |
| **Storage Account (AI)** | AI Foundry blob storage and NL2SQL data |
| **Storage Account (Dashboard)** | Static website hosting for azure-dashboard |
| **AI Foundry Hub + Project** | Azure AI services, model deployments, agent service |
| **Cosmos DB** | Thread storage for AI Foundry agent service |
| **AI Search** | Vector search for RAG scenarios |
| **Application Insights** | Telemetry and distributed tracing |
| **Log Analytics Workspace** | Centralized logging |

### Terraform Variables

Key variables in `terraform.tfvars`:

| Variable | Description |
|----------|-------------|
| `subscription_id` | Azure subscription ID |
| `region` | Primary Azure region (default: westus3) |
| `region_aifoundry` | AI Foundry region (default: eastus2) |
| `frontend_app_client_id` | App Registration for frontend auth |
| `mcp_app_client_id` | App Registration for MCP auth |
| `github_actions_principal_id` | Service principal object ID for GitHub Actions |
| `auth_enabled` | Enable/disable Azure AD auth (default: true) |

### Terraform Outputs

| Output | Description |
|--------|-------------|
| `frontend_url` | Container App URL for Next.js frontend |
| `api_url` | Container App URL for backend API |
| `mcp_url` | Container App URL for MCP server |
| `dashboard_url` | Static website URL for azure-dashboard |
| `dashboard_storage_account_name` | Storage account name for dashboard deployment |
| `appinsights_instrumentation_key` | Application Insights instrumentation key (GUID) |
| `appinsights_ingestion_endpoint` | Application Insights ingestion endpoint URL |

## GitHub Actions Deployment

Four workflows handle CI/CD deployment to Azure:

| Workflow | Trigger Path | Deploys To |
|----------|--------------|------------|
| `deploy-api.yml` | `backend/api/**` | Container App (API) |
| `deploy-frontend.yml` | `frontend/**` | Container App (Frontend) |
| `deploy-mcp.yml` | `backend/mcp/**` | Container App (MCP) |
| `deploy-dashboard.yml` | `monitoring/azure-dashboard/**` | Storage static website |

### Required GitHub Variables

Configure these in Settings → Secrets and variables → Actions → Variables:

| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `AZURE_CONTAINER_REGISTRY` | ACR name (without .azurecr.io) |
| `AZURE_FRONTEND_CONTAINER_APP_NAME` | Frontend container app name |
| `AZURE_API_CONTAINER_APP_NAME` | API container app name |
| `AZURE_MCP_CONTAINER_APP_NAME` | MCP container app name |
| `AZURE_DASHBOARD_STORAGE_ACCOUNT` | Dashboard storage account name |
| `NEXT_PUBLIC_AZURE_AD_CLIENT_ID` | Frontend app registration client ID |
| `NEXT_PUBLIC_AZURE_AD_TENANT_ID` | Tenant ID for frontend auth |
| `NEXT_PUBLIC_AUTH_ENABLED` | Enable auth in frontend (true/false) |
| `NEXT_PUBLIC_APPINSIGHTS_INGESTION_ENDPOINT` | App Insights ingestion endpoint (optional) |
| `AGENT_API_BASE_URL` | Backend API URL for frontend |
| `VITE_AZURE_CLIENT_ID` | Dashboard app registration client ID |
| `VITE_LOG_ANALYTICS_WORKSPACE_ID` | Log Analytics workspace ID for dashboard |

### Azure Dashboard Deployment

The `monitoring/azure-dashboard` is a Vite + React app that queries Application Insights for trace visualization. It deploys to Azure Storage static website hosting.

Environment variables are baked in at build time:
```env
VITE_AZURE_CLIENT_ID=...       # App Registration for MSAL auth
VITE_AZURE_TENANT_ID=...       # Azure AD tenant
VITE_LOG_ANALYTICS_WORKSPACE_ID=... # Log Analytics workspace to query
```

## Code Style Guidelines

### Python
- Use type hints for all function parameters and return values
- Use `from __future__ import annotations` for forward references
- Follow PEP 8 naming conventions
- Use `logging` module (not print statements)
- Use `async/await` for I/O operations

### TypeScript/React
- Use functional components with hooks
- Define interfaces for all data structures
- Use `"use client"` directive for client components
- Prefer named exports over default exports for components
- Use Tailwind CSS for styling

### General
- Keep functions focused and single-purpose
- Write descriptive docstrings/comments for complex logic
- Handle errors gracefully with proper error messages
- Use environment variables for configuration

## Important Notes

1. **MCP is required** - The backend requires the MCP server to be running for flight data
2. **A2A is optional** - Recommendations work without the A2A agent (fallback to mock data)
3. **Patches must load first** - `backend/api/patches/` package must be imported before other modules
4. **AG-UI protocol** - Agent communication uses Server-Sent Events (SSE)
5. **Thread management** - Uses `ResponsesApiThreadMiddleware` with a ContextVar to track CopilotKit threadId for telemetry correlation
6. **Filter state** - Frontend tracks `activeFilter` locally; synced to backend via `useCopilotReadable` context
7. **Additive filters** - `filter_flights` merges with existing filters; use `reset_filters` to clear first
8. **Monitoring** - OpenTelemetry configured in `monitoring.py`; supports Azure Monitor and OTLP exporters
9. **System prompts** - Agent instructions stored in `backend/api/agents/prompts/` as markdown files for easy editing

## Known Issues and Workarounds

### Duplicate Tool Calls
The Responses API sometimes sent duplicate tool calls with different run IDs. This was fixed natively in agent-framework >= 1.0.0b260210 (PR #3635). The `agui_event_stream` patch no longer needs to suppress duplicates.

### Clear Button Behavior
The Clear button (`✕ Clear` in the filter bar) **bypasses the LLM entirely** for reliability:
1. Directly resets `displayFilter` to `DEFAULT_FILTER`
2. Refetches all flights via REST API
3. LLM is informed of the new state via `useCopilotReadable` context on next interaction

This ensures filter clearing is deterministic and doesn't depend on LLM interpretation.

### Streaming and UI Interactions
If a user interacts with the UI (e.g., clicks Clear) while the agent is streaming a response, a "Thread already running" error may occur. This is a known limitation of the current architecture.

## Monitoring and Observability

The backend uses OpenTelemetry for distributed tracing, configured in `backend/api/monitoring.py`.

### Configuration

Enable observability by setting environment variables:

```env
# Enable OpenTelemetry instrumentation
ENABLE_INSTRUMENTATION=true

# Telemetry mode: "appinsights" (default) or "otlp"
TELEMETRY_MODE=appinsights

# Azure Monitor (for TELEMETRY_MODE=appinsights)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# OTLP endpoint (for TELEMETRY_MODE=otlp)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Enable console exporters for debugging
ENABLE_CONSOLE_EXPORTERS=true

# Log prompts and responses (development only - sensitive data!)
ENABLE_SENSITIVE_DATA=true
```

### Telemetry Backends

| Mode | Configuration | Use Case |
|------|---------------|----------|
| `appinsights` | `APPLICATIONINSIGHTS_CONNECTION_STRING` | Production monitoring, Azure Application Insights |
| `otlp` | `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` | Local dev with Aspire Dashboard, Jaeger, or Grafana Tempo |
| (any) | `ENABLE_CONSOLE_EXPORTERS=true` | Debugging, quick trace inspection |

### Instrumentation Coverage

The `monitoring.py` module configures:
- **Azure SDK tracing** - Traces Azure AI Foundry/Inference API calls
- **FastAPI tracing** - Traces HTTP requests to the backend
- **Agent Framework tracing** - Traces agent workflows and tool execution
- **Conversation ID injection** - Adds `gen_ai.conversation_id` to all spans for correlation

### Sample Queries

**Azure Monitor (KQL)**:
```kql
// All spans for a conversation
dependencies
| where customDimensions.gen_ai_conversation_id == "your-thread-id"
| order by timestamp asc
```

**Grafana Tempo (TraceQL)**:
```traceql
{ span.gen_ai.conversation_id = "your-thread-id" }
```

## Thread Mapping and Telemetry

### Thread ID Architecture

CopilotKit generates a UUID `threadId` on the frontend for conversation continuity. This ID flows through the system:

1. **Frontend**: CopilotKit generates `threadId` (e.g., `a24ea2c1-fd51-4354-af5e-f5f8ab9e3bcf`)
2. **AG-UI Protocol**: Sent in SSE request body as `threadId`
3. **Backend Middleware**: Extracted and stored in shared ContextVar (`_current_agui_thread_id`)
4. **Azure AI Foundry**: Uses CopilotKit threadId as `previous_response_id` chain for conversation continuity
5. **Telemetry**: CopilotKit threadId injected as `gen_ai.conversation_id` for correlation

### Telemetry Correlation

All telemetry spans include `gen_ai.conversation_id` (the CopilotKit threadId) for querying:

```kql
// Find all telemetry for a conversation
dependencies
| where customDimensions.gen_ai_conversation_id == "a24ea2c1-fd51-4354-af5e-f5f8ab9e3bcf"
```

**Telemetry Backends Supported**:
- **Azure Monitor/Application Insights**: Via `azure-monitor-opentelemetry`
- **Aspire Dashboard**: Via OTLP exporter (local dev)
- **Grafana Tempo**: Via OTLP exporter (supports TraceQL queries by conversation_id)

**Note**: Each HTTP POST to `/logistics` creates a new `operation_Id` (trace). Use `gen_ai.conversation_id` to correlate all requests in a conversation.

### Patches Package (`backend/api/patches/`)
The patches package applies context synchronization and telemetry workarounds. Each patch is in its own file:

| Patch | File | Purpose |
|-------|------|----------|
| AG-UI Context Sync | `agui_event_stream.py` | Extracts CopilotKit threadId, syncs activeFilter to ContextVar, sets OTel conversation_id span attributes |
| Conversation ID (Responses) | `conversation_id_injection.py` | Injects `gen_ai.conversation_id` into Responses API telemetry spans |
| Tool Execution Span | `conversation_id_injection.py` | Adds `gen_ai.conversation_id` to agent-framework tool execution spans |

Patches can be disabled via environment variables:
- `PATCH_AGUI_CONTEXT_SYNC=false`
- `PATCH_CONVERSATION_ID_INJECTION=false`
- `PATCH_TOOL_EXECUTION_SPAN=false`
