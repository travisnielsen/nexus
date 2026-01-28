# Agent Trace Dashboard

A React-based dashboard for visualizing agent conversation traces from Azure Application Insights / Log Analytics.

This is a port of the original `conversation-viewer.html` (which queries Grafana Tempo) to use Azure's native telemetry backend.

## Features

- 🔐 **Azure AD Authentication** - Sign in with your Microsoft account using MSAL
- 🔍 **Conversation Search** - Query traces by conversation ID
- 📋 **Recent Conversations** - Browse recently active conversation sessions
- 🌳 **Hierarchical Tree View** - Navigate runs, steps, and tool calls
- 📊 **Detail Panel** - View input/output messages, tool arguments/results, and metadata
- 🎨 **VS Code Dark Theme** - Matches the original viewer's aesthetic

## Prerequisites

1. **Azure AD App Registration** with:
   - API permissions for `https://api.loganalytics.io/.default`
   - Redirect URI: `http://localhost:5173` (for development)

2. **Application Insights** connected to a **Log Analytics workspace**

3. **Reader access** to the Log Analytics workspace

## Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env.local
   ```

2. Edit `.env.local` with your Azure configuration:
   ```env
   VITE_AZURE_CLIENT_ID=your-client-id
   VITE_AZURE_TENANT_ID=your-tenant-id
   VITE_LOG_ANALYTICS_WORKSPACE_ID=your-workspace-id
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

5. Open http://localhost:5173

## Azure AD App Registration

1. Go to **Azure Portal** → **Microsoft Entra ID** → **App registrations**
2. Click **New registration**
3. Name: `Agent Trace Dashboard`
4. Supported account types: **Single tenant** (or as needed)
5. Redirect URI: **Single-page application (SPA)** → `http://localhost:5173`
6. After creation, go to **API permissions**:
   - Click **Add a permission**
   - Select **APIs my organization uses**
   - Search for `Log Analytics API`
   - Select **Delegated permissions** → **Data.Read**
   - Click **Add permissions**
   - (Optional) Click **Grant admin consent** for the organization

## Data Requirements

The dashboard queries the `dependencies` and `traces` tables for spans with these attributes:

| Attribute | Description |
|-----------|-------------|
| `gen_ai_conversation_id` or `gen_ai.conversation.id` | Conversation/thread ID |
| `gen_ai.operation.name` | Operation type (`chat`, `execute_tool`, etc.) |
| `gen_ai.request.model` | LLM model name |
| `gen_ai.tool.name` | Tool function name |
| `gen_ai.tool.call.arguments` | Tool input arguments (JSON) |
| `gen_ai.tool.call.result` | Tool output result (JSON) |
| `gen_ai.input.messages` | Input messages (JSON) |
| `gen_ai.output.messages` | Output messages (JSON) |
| `gen_ai.usage.input_tokens` | Input token count |
| `gen_ai.usage.output_tokens` | Output token count |

These attributes are automatically captured by the backend's OpenTelemetry instrumentation.

## Sample KQL Queries

Find all spans for a conversation:
```kql
dependencies
| where customDimensions.gen_ai_conversation_id == "your-conversation-id"
| project timestamp, name, duration, customDimensions
| order by timestamp asc
```

List recent conversations:
```kql
dependencies
| where timestamp > ago(24h)
| where isnotempty(customDimensions.gen_ai_conversation_id)
| summarize FirstSeen = min(timestamp), SpanCount = count() 
  by tostring(customDimensions.gen_ai_conversation_id)
| order by FirstSeen desc
| take 20
```

## Comparison with Tempo Viewer

| Feature | Tempo (conversation-viewer.html) | Application Insights (this app) |
|---------|----------------------------------|--------------------------------|
| Backend | Grafana Tempo | Azure Log Analytics |
| Query Language | TraceQL | KQL |
| Authentication | None (local) | Microsoft Entra ID |
| Deployment | Static HTML | React SPA |
| Trace Correlation | `traceID` / `spanId` | `operation_Id` / `id` |

## Project Structure

```
trace-dashboard/
├── src/
│   ├── App.tsx                    # Main app component
│   ├── main.tsx                   # Entry point with MSAL provider
│   ├── index.css                  # Global styles
│   ├── components/
│   │   ├── ConfigPanel.tsx        # Workspace configuration
│   │   ├── DetailPanel.tsx        # Span detail view
│   │   ├── LoginButton.tsx        # Auth components
│   │   ├── Sidebar.tsx            # Search and tree container
│   │   └── TreeView.tsx           # Hierarchical span tree
│   └── lib/
│       ├── logAnalyticsClient.ts  # Log Analytics API client
│       ├── msalConfig.ts          # MSAL configuration
│       ├── types.ts               # TypeScript interfaces
│       └── utils.ts               # Tree building, formatting
├── .env.example                   # Environment template
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

## Building for Production

```bash
npm run build
```

The output will be in the `dist/` directory, ready to be deployed to any static hosting service.
