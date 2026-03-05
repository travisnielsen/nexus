# Recommendations Agent (A2A Server)

This is a simple FastAPI-based agent that hosts an A2A (Agent-to-Agent) endpoint. It provides logistics recommendations when called by other agents. It uses Microsoft Foundry (Azure AI Client) just like the main API.

## Setup

1. Bootstrap dependencies from the monorepo root (recommended):

```bash
./devsetup.sh
```

Or install only this service dependencies:

```bash
cd src/backend/agent-a2a
uv sync --dev
```

1. Configure environment variables (create a `.env` file):

```bash
# Required: Microsoft Foundry / Azure AI Project settings
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project-id
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o-mini

# Server port (optional, defaults to 5002)
PORT=5002
```

1. Authenticate with Azure:

```bash
az login
```

## Running the Agent

```bash
# From the agent-a2a directory
uv run uvicorn main:app --reload --port 5002
```

Or using the Python module:

```bash
python main.py
```

## Endpoints

- `POST /` - A2A/AG-UI endpoint for agent communication
- `GET /health` - Health check endpoint

## Calling from the API

The main API can call this agent using the `get_recommendations` tool, which uses A2A protocol to communicate with this agent.

Set the `RECOMMENDATIONS_AGENT_URL` environment variable in the API to point to this agent:

```bash
RECOMMENDATIONS_AGENT_URL=http://localhost:5002
```
