# Enterprise Data Agent

This is an agent-assited dashboard. It leverages [Microsoft Agent Framework](https://aka.ms/agent-framework) (MAF) as an agent orchestrator and [CopilotKit](https://www.copilotkit.ai/) for the core user experience. These two pieces work together using the MAF implementation of the AG-UI protocol in the [agent-framework-ag-ui](https://pypi.org/project/agent-framework-ag-ui/) package. The code used in this sample was originated from [this template](https://github.com/CopilotKit/with-microsoft-agent-framework-python) created by the CopilotKit team.

## Prerequisites

- Azure OpenAI credentials (for the Microsoft Agent Framework agent)
- Python 3.12+
- uv
- Node.js 20+ 
- Any of the following package managers:
  - pnpm (recommended)
  - npm
  - yarn
  - bun

It is assumed you have administrative permissions to an Azure subscription as well as the ability to register applications in Entra ID.

## Getting Started

### Deploy Azure Infrastructure

Coming soon

### Install dependencies

Install dependencies using your preferred package manager:

   ```bash
   # Using pnpm (recommended)
   pnpm install

   # Using npm
   npm install

   # Using yarn
   yarn install

   # Using bun
   bun install
   ```

   > **Note:** This automatically sets up the Python environment as well. If you have manual issues, you can run: `npm run install:agent`

### Register an App ID in Entra ID

This repo supports user-level authentication to the agent API, which supports enterprise security as well as documenting user feedback. The application can be created using: [create-chat-app.ps1](scripts/create-chat-app.ps1). Be sure to sign-into your Entra ID tenant using `az login` first.

### Set environment variables

Using the output from the application enrollment script, set up your agent credentials. The backend automatically uses Azure when the Azure env vars below are present. Create an `.env` file inside the `agent` folder with one of the following configurations:
  
   ```env
   # Microsoft Foundry settings
   AZURE_OPENAI_ENDPOINT=https://[your-resource].services.ai.azure.com/
   AZURE_OPENAI_PROJECT_ENDPOINT=https://[your-resource].services.ai.azure.com/api/projects/[your-project]
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o

   # Entra ID Authentication
   AZURE_AD_CLIENT_ID=[your-app-id]
   AZURE_AD_TENANT_ID=[your-tenant-id]
   ```

> [!IMPORTANT]
> The Entra ID section is optional. When the two environment variables are set, the API will require a valid token issued by the source tenant with the correct target scope. If you don't require user-level authorization to the API, you can delete this section.
 
Next, create a new `.env.local` file within the `frontend` directory and populate the values. You can use the [.env.example](frontend/.env.example) as a reference.

   ```env
   NEXT_PUBLIC_AZURE_AD_CLIENT_ID=your-client-id-here
   NEXT_PUBLIC_AZURE_AD_TENANT_ID=your-tenant-id-here
   ```

### Disabling Authentication (Development Only)

For local development or testing purposes, you can disable authentication entirely by setting the `AUTH_ENABLED` environment variable to `false` on both the API and frontend.

**API (.env file in the `backend` folder):**
   ```env
   AUTH_ENABLED=false
   ```

**Frontend (.env.local file in the `frontend` folder):**
   ```env
   NEXT_PUBLIC_AUTH_ENABLED=false
   ```

> [!WARNING]
> Do NOT use `AUTH_ENABLED=false` in production environments. This setting allows anonymous access to the API without any authentication or authorization checks.

### Start the development server

The following commands can be used to start the enviroment locally:

   ```bash
   # Using pnpm
   pnpm dev

   # Using npm
   npm run dev

   # Using yarn
   yarn dev

   # Using bun
   bun run dev
   ```

   This will start both the UI and the Microsoft Agent Framework server concurrently.

## Available Scripts

The following scripts can also be run using your preferred package manager:

- `dev` – Starts both UI and agent servers in development mode
- `dev:debug` – Starts development servers with debug logging enabled
- `dev:ui` – Starts only the Next.js UI server
- `dev:agent` – Starts only the Microsoft Agent Framework server
- `build` – Builds the Next.js application for production
- `start` – Starts the production server
- `lint` – Runs ESLint for code linting
- `install:agent` – Installs Python dependencies for the agent

## AG-UI and CopilotKit Features

This application demonstrates several key features from the [AG-UI protocol](https://docs.ag-ui.com/) and [CopilotKit](https://docs.copilotkit.ai/):

| Feature | Used? | Details |
|---------|-------|---------|
| **Agentic Chat** | ✅ Yes | `useCopilotAction` with handlers like `reload_all_flights`, `fetch_flight_details` that the LLM calls to execute frontend logic |
| **Backend Tool Rendering** | ✅ Yes | `useRenderToolCall` renders progress UI in the chat for backend tools (`filter_flights`, `analyze_flights`, `reset_filters`, `get_recommendations`, etc.) |
| **Human in the Loop** | ⚠️ Partial | `HumanInTheLoopOrchestrator` is in the orchestrator chain but no tools currently require approval |
| **Agentic Generative UI** | ❌ No | No long-running background tasks with streaming UI updates |
| **Tool-based Generative UI** | ⚠️ Partial | `useCopilotAction` with `render` exists for `display_flights`, `display_flight_details`, `display_historical_data` but actions are disabled with minimal output |
| **Shared State** | ⚠️ Partial | `useCoAgent` declares shared state but frontend uses local state + REST API instead |
| **Predictive State Updates** | ❌ No | Not used - frontend fetches data via REST API when tools complete |

### Feature Examples

#### Agentic Chat (Frontend Actions)

Frontend actions allow the LLM to invoke client-side handlers:

```tsx
useCopilotAction({
  name: "reload_all_flights",
  description: "Clear all filters and load ALL flights into dashboard.",
  parameters: [{ name: "count", type: "number", required: false }],
  handler: async ({ count }) => {
    const flights = await refetchFlights({ limit: count || 100 });
    setDisplayFlights(flights);
    return `Dashboard now shows ${flights.length} flights.`;
  },
});
```

#### Backend Tool Rendering

Render custom UI in the chat when backend tools execute:

```tsx
useRenderToolCall({
  name: "filter_flights",
  render: ({ args, status }) => (
    <div className="flex items-center gap-2 text-sm">
      {status !== 'complete' ? (
        <span>🔄 Fetching flights...</span>
      ) : (
        <span>✅ Loaded flights</span>
      )}
    </div>
  ),
});
```

#### Shared State

Bidirectional state sync between React and the Python agent:

```tsx
const { state, setState } = useCoAgent<LogisticsAgentState>({
  name: "logistics_agent",
  initialState: initialLogisticsState,
});

// React to tool completion via useRenderToolCall (not state sync)
useRenderToolCall({
  name: "filter_flights",
  render: ({ status }) => {
    if (status === 'complete') {
      refetchFlights(mergedFilter);  // Fetch via REST API
    }
  },
});
```

#### Backend Tools

Python tools the LLM can invoke via the agent:

```python
@ai_function(
    name="filter_flights",
    description="Filter flights in the dashboard.",
)
def filter_flights(
    route_from: Annotated[str | None, Field(description="Origin airport code")] = None,
    route_to: Annotated[str | None, Field(description="Destination airport code")] = None,
) -> dict:
    return {"message": "Loading flights...", "activeFilter": {...}}
```

## Docker

You can run the services using Docker. Each service has its own Dockerfile.

### Building Images

```bash
# Build the backend (API) image
docker build -t logistics-backend -f backend/Dockerfile backend/

# Build the frontend image
docker build -t logistics-frontend -f frontend/Dockerfile frontend/

# Build the A2A recommendations agent image
docker build -t logistics-a2a-agent -f agent-a2a/Dockerfile agent-a2a/
```

### Running Containers

```bash
# Run the backend API (port 8000)
docker run -d --name backend \
  -p 8000:8000 \
  -e AZURE_AI_PROJECT_ENDPOINT=https://[your-resource].services.ai.azure.com/api/projects/[your-project] \
  -e AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini \
  -e AZURE_AD_CLIENT_ID=[your-client-id] \
  -e AZURE_AD_TENANT_ID=[your-tenant-id] \
  -e AUTH_ENABLED=false \
  -e RECOMMENDATIONS_AGENT_URL=http://localhost:5002 \
  logistics-backend

# Run the A2A recommendations agent (port 5002)
docker run -d --name a2a-agent \
  -p 5002:5002 \
  -e AZURE_AI_PROJECT_ENDPOINT=https://[your-resource].services.ai.azure.com/api/projects/[your-project] \
  -e AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini \
  logistics-a2a-agent

# Run the frontend (port 3000)
docker run -d --name frontend \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  logistics-frontend
```

### Docker Compose (Optional)

For running all services together, you can use Docker Compose:

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=${AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}
      - RECOMMENDATIONS_AGENT_URL=http://a2a-agent:5002
    depends_on:
      - a2a-agent

  a2a-agent:
    build:
      context: ./agent-a2a
      dockerfile: Dockerfile
    ports:
      - "5002:5002"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

Run with:
```bash
docker compose up -d
```
