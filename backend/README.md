# Backend API

FastAPI-based backend for the Enterprise Data Agent. Uses Microsoft Agent Framework (MAF) for agent orchestration and CopilotKit's AG-UI protocol for frontend communication.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + MAF)                         │
│                         Port: 8000                                   │
├─────────────────────────────────────────────────────────────────────┤
│  main.py              - FastAPI app, REST endpoints, AG-UI SSE      │
│  clients.py           - Chat client factory (Azure AI integration)  │
│  monitoring.py        - OpenTelemetry observability                 │
├─────────────────────────────────────────────────────────────────────┤
│  agents/                                                             │
│    logistics_agent.py - Agent configuration and system prompt       │
│    tools/             - LLM-callable tool functions                 │
│    utils/             - Utility modules (not LLM-callable)          │
├─────────────────────────────────────────────────────────────────────┤
│  middleware/          - Auth and thread management                  │
│  patches/             - Critical workarounds (load first!)          │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
backend/
├── main.py                 # FastAPI app, REST endpoints, agent setup
├── clients.py              # Chat client factory (Responses/Assistants API)
├── monitoring.py           # OpenTelemetry observability setup
├── pyproject.toml          # Python dependencies (uv)
├── agents/
│   ├── logistics_agent.py  # Agent configuration and system prompt
│   ├── tools/              # Agent tool implementations (LLM-callable)
│   │   ├── __init__.py
│   │   ├── filter_tools.py         # filter_flights, reset_filters
│   │   ├── analysis_tools.py       # analyze_flights
│   │   ├── chart_tools.py          # get_historical_payload, get_predicted_payload
│   │   └── recommendation_tools.py # get_recommendations (A2A)
│   └── utils/              # Utility modules (not LLM-callable)
│       ├── __init__.py
│       ├── mcp_client.py           # HTTP client for MCP server
│       └── data_helpers.py         # Shared data access functions
├── middleware/
│   ├── auth.py             # Azure AD authentication
│   ├── responses_api.py    # Responses API thread middleware
│   └── assistants_api.py   # Assistants API thread middleware
└── patches/                # Critical workarounds (must import first)
    ├── __init__.py
    └── agui_event_stream.py # AG-UI event stream fixes
```

## Agent Tools

| Tool | File | Purpose |
|------|------|---------|
| `filter_flights` | `filter_tools.py` | Filter dashboard by route, utilization, risk (additive) |
| `reset_filters` | `filter_tools.py` | Clear all filters and show all flights |
| `analyze_flights` | `analysis_tools.py` | Answer questions about displayed data |
| `get_recommendations` | `recommendation_tools.py` | Get AI recommendations via A2A agent |
| `get_historical_payload` | `chart_tools.py` | Get historical payload data for charts |
| `get_predicted_payload` | `chart_tools.py` | Get predicted payload data for charts |

## Data Flow

All flight data comes from the MCP server:

```
Frontend → Backend REST API → MCP Server (source of truth)
                ↓
         Agent Tools → MCP Client (utils/mcp_client.py)
```

**Note**: The backend has NO local data files. All data is fetched from the MCP server.

## Setup

```bash
cd backend
uv sync
```

## Running

```bash
# Development with hot reload
uv run uvicorn main:app --port 8000 --reload

# Or using the npm script from root
npm run dev:agent
```

## Configuration

Create a `.env` file:

```env
# Azure AI / Microsoft Foundry
AZURE_AI_PROJECT_ENDPOINT=https://...
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_AI_API_TYPE=responses  # or "assistants"

# Authentication (optional)
AZURE_AD_CLIENT_ID=...
AZURE_AD_TENANT_ID=...
AUTH_ENABLED=false  # Development only (default: true)

# MCP Server
MCP_SERVER_URL=http://localhost:8001

# A2A Agent
RECOMMENDATIONS_AGENT_URL=http://localhost:5002

# Logging
AGENT_FRAMEWORK_LOG_LEVEL=WARNING  # DEBUG for verbose
```

## REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/logistics/data/flights` | GET | Get flights with filtering |
| `/logistics/data/flights/{id}` | GET | Get a specific flight |
| `/logistics/data/summary` | GET | Get flight statistics |
| `/logistics/data/historical` | GET | Get historical data with predictions |
| `/copilotkit` | POST | AG-UI SSE endpoint for CopilotKit |
| `/recommendations/feedback` | POST | Submit feedback on recommendations |

## Patches

The `patches/` package applies critical workarounds that must load before other modules:

| Patch | Purpose |
|-------|---------|
| `agui_event_stream.py` | Buffers orphaned text messages, deduplicates tool calls, syncs context |

Patches can be disabled via environment variables:
- `PATCH_AGUI_TEXT_MESSAGE_END=false`
