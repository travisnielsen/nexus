# Observability and Tracing

This directory contains tools and dashboards for monitoring and visualizing agent traces from the Logistics Dashboard.

## Table of Contents

- [Observability and Tracing](#observability-and-tracing)
  - [Table of Contents](#table-of-contents)
  - [How Tracing Works](#how-tracing-works)
    - [Conversation ID Generation](#conversation-id-generation)
    - [Backend Capture and Propagation](#backend-capture-and-propagation)
    - [Span Instrumentation](#span-instrumentation)
  - [Observability Modes](#observability-modes)
    - [Azure Application Insights Mode](#azure-application-insights-mode)
    - [Self-Hosted OTLP Mode](#self-hosted-otlp-mode)
  - [Configuration Reference](#configuration-reference)
  - [Dashboard Options](#dashboard-options)
    - [Azure Dashboard](#azure-dashboard)
    - [OTEL Dashboard](#otel-dashboard)
  - [Comparison](#comparison)

---

## How Tracing Works

The solution uses OpenTelemetry to capture distributed traces across all agent interactions. Every conversation is tagged with a unique identifier that flows through all spans, enabling end-to-end visibility.

### Conversation ID Generation

1. **CopilotKit Frontend**: When a user starts a chat session, CopilotKit generates a unique `threadId` (UUID format, e.g., `a24ea2c1-fd51-4354-af5e-f5f8ab9e3bcf`). This ID persists for the lifetime of the conversation.

2. **AG-UI Protocol**: The `threadId` is sent to the backend in every SSE request body as part of the AG-UI protocol payload.

3. **Frontend Context Sync**: The frontend also sends the current UI state (including active filters) via `useCopilotReadable`, which the backend uses for context-aware responses.

### Backend Capture and Propagation

The backend captures the `threadId` and propagates it through the telemetry system:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend (CopilotKit)                                              │
│  Generates: threadId = "a24ea2c1-fd51-4354-af5e-f5f8ab9e3bcf"      │
└────────────────────────────┬────────────────────────────────────────┘
                             │ SSE POST /logistics (AG-UI Protocol)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AG-UI Event Stream Patch (patches/agui_event_stream.py)            │
│  - Extracts threadId from request body                              │
│  - Stores in ContextVar: _current_agui_thread_id                    │
│  - Creates root conversation span with gen_ai.conversation.id       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Thread Middleware (middleware/responses_api.py)                    │
│  - Maps threadId to Azure response_id chain (Responses API)         │
│  - Or maps to Azure thread_id (Assistants API)                      │
│  - Exposes get_current_agui_thread_id() for other modules           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Conversation ID Injection (patches/conversation_id_injection.py)   │
│  - Patches Azure SDK telemetry to include gen_ai.conversation.id    │
│  - Patches Agent Framework tool execution spans                     │
│  - Ensures all spans in a conversation are correlated               │
└─────────────────────────────────────────────────────────────────────┘
```

### Span Instrumentation

The following spans are captured with `gen_ai.conversation.id`:

| Span Type | Source | Key Attributes |
|-----------|--------|----------------|
| `chat` | Azure AI Foundry SDK | `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.request.model` |
| `execute_tool` | Agent Framework | `gen_ai.tool.name`, `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result` |
| `invoke_agent` | Agent Framework | `gen_ai.agent.name` |
| HTTP requests | FastAPI/urllib3 | Standard HTTP span attributes |

---

## Observability Modes

The backend supports two telemetry modes, configured via the `TELEMETRY_MODE` environment variable.

### Azure Application Insights Mode

**Best for**: Production deployments, Azure-native monitoring

```env
ENABLE_INSTRUMENTATION=true
TELEMETRY_MODE=appinsights
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=...
```

This mode uses the Azure Monitor OpenTelemetry SDK to send traces directly to Application Insights. Traces are stored in the connected Log Analytics workspace and can be queried with KQL.

**Where to set the connection string:**

| Location | File | Purpose |
|----------|------|---------|
| Local development | `backend/.env` | `APPLICATIONINSIGHTS_CONNECTION_STRING=...` |
| Local development (example) | `backend/.env.example` | Template for new developers |
| Terraform deployment | `infra/workload.tf` (line ~595) | Azure Container App environment variable |
| Docker Compose | Can be added to `docker-compose.yml` | Container orchestration |

**How to find your connection string:**

1. Go to Azure Portal → Application Insights resource
2. Click **Overview** in the left menu
3. Find **Connection String** in the Essentials section
4. Copy the full string (starts with `InstrumentationKey=`)

### Self-Hosted OTLP Mode

**Best for**: Local development, self-hosted observability stacks

```env
ENABLE_INSTRUMENTATION=true
TELEMETRY_MODE=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

This mode sends traces via OTLP (gRPC) to any compatible backend:
- **Grafana Tempo** (included in `otel-dashboard/`)
- **Jaeger**
- **.NET Aspire Dashboard**
- **Honeycomb, Datadog, etc.**

Optional debug output:
```env
ENABLE_CONSOLE_EXPORTERS=true  # Print spans to console
```

---

## Configuration Reference

All observability settings in `backend/.env`:

```env
# Enable/disable all telemetry
ENABLE_INSTRUMENTATION=true

# Telemetry backend: "appinsights" or "otlp"
TELEMETRY_MODE=appinsights

# Azure Monitor (for TELEMETRY_MODE=appinsights)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...

# OTLP endpoint (for TELEMETRY_MODE=otlp)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Log prompts and responses (CAUTION: sensitive data!)
ENABLE_SENSITIVE_DATA=true

# Print spans to console for debugging
ENABLE_CONSOLE_EXPORTERS=false
```

---

## Dashboard Options

### Azure Dashboard

📁 **Location**: `monitoring/azure-dashboard/`

A React-based dashboard that queries Azure Application Insights / Log Analytics directly using the REST API.

**Features:**
- 🔐 Azure AD authentication via MSAL
- 📋 Recent conversations list
- 🌳 Hierarchical tree view (Conversation → Runs → Steps → Tools)
- 📊 Input/Output and Metadata panels
- 🔢 Token usage and duration tracking at all levels

**Prerequisites:**
- Azure AD App Registration with `https://api.loganalytics.io/.default` permission
- Application Insights connected to a Log Analytics workspace
- Reader access to the workspace

**Quick Start:**
```bash
cd monitoring/azure-dashboard
cp .env.example .env.local
# Edit .env.local with your Azure configuration
npm install
npm run dev
```

**Querying traces:**
```kql
AppDependencies
| where Properties["gen_ai.conversation.id"] == "your-conversation-id"
| order by TimeGenerated asc
```

---

### OTEL Dashboard

📁 **Location**: `monitoring/otel-dashboard/`

A Docker Compose stack with Grafana Tempo for self-hosted trace visualization.

**Components:**
- **OpenTelemetry Collector** - Receives OTLP traces (ports 4317/4318)
- **Grafana Tempo** - Stores and indexes traces
- **Grafana** - Web UI for trace visualization (port 3001)
- **conversation-viewer.html** - Custom trace viewer for agent conversations

**Quick Start:**
```bash
cd monitoring/otel-dashboard
docker compose up -d
# Backend automatically sends to localhost:4317
```

**Access:**
- Grafana: http://localhost:3001
- Conversation Viewer: Open `conversation-viewer.html` in browser

**Querying traces (TraceQL):**
```traceql
{ span.gen_ai.conversation.id = "your-conversation-id" }
```

---

## Comparison

| Feature | Azure Dashboard | OTEL Dashboard |
|---------|-----------------|----------------|
| **Deployment** | Azure cloud | Self-hosted (Docker) |
| **Data Retention** | 30-90 days (configurable) | Local storage |
| **Authentication** | Azure AD | None (local only) |
| **Query Language** | KQL | TraceQL |
| **Best For** | Production, compliance | Development, debugging |
| **Cost** | Azure billing | Free (self-hosted) |
| **Custom Viewer** | ✅ React app | ✅ HTML + Tempo API |
