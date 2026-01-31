# AG-UI and CopilotKit Features

This application demonstrates several key features from the [AG-UI protocol](https://docs.ag-ui.com/) and [CopilotKit](https://docs.copilotkit.ai/).

## Feature Overview

| Feature | Used? | Details |
|---------|-------|---------|
| **Agentic Chat** | ✅ Yes | `useCopilotAction` with handlers like `reload_all_flights`, `fetch_flight_details` that the LLM calls to execute frontend logic |
| **Backend Tool Rendering** | ✅ Yes | `useRenderToolCall` renders progress UI in the chat for backend tools (`filter_flights`, `analyze_flights`, `reset_filters`, `get_recommendations`, etc.) |
| **Human in the Loop** | ⚠️ Partial | `HumanInTheLoopOrchestrator` is in the orchestrator chain but no tools currently require approval |
| **Agentic Generative UI** | ❌ No | No long-running background tasks with streaming UI updates |
| **Tool-based Generative UI** | ⚠️ Partial | `useCopilotAction` with `render` exists for `display_flights`, `display_flight_details`, `display_historical_data` but actions are disabled with minimal output |
| **Shared State** | ⚠️ Partial | `useCoAgent` declares shared state but frontend uses local state + REST API instead |
| **Predictive State Updates** | ❌ No | Not used - frontend fetches data via REST API when tools complete |

## Feature Examples

### Agentic Chat (Frontend Actions)

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

### Backend Tool Rendering

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

### Shared State

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

### Backend Tools

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
