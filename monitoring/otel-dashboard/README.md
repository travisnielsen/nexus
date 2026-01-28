# OpenTelemetry Dashboard with Grafana Tempo

This folder contains a Docker Compose setup for visualizing distributed traces from the GOC Capacity Dashboard agent using Grafana Tempo.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI + MAF)                         │
│                         Port: 8000                                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ OTLP (gRPC/HTTP)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OpenTelemetry Collector                            │
│              Ports: 4317 (gRPC), 4318 (HTTP)                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │ OTLP
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Grafana Tempo                                  │
│                    Port: 3200 (HTTP API)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Grafana                                     │
│                       Port: 3001 (UI)                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Start the Tracing Stack

```bash
cd otel-dashboard
docker compose up -d
```

### 2. Configure the Backend

Set the following environment variables in your backend `.env` file:

```env
ENABLE_INSTRUMENTATION=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### 3. Access Grafana

Open [http://localhost:3001](http://localhost:3001) in your browser.

- **No login required** - Anonymous access is enabled for development
- Navigate to **Explore** → Select **Tempo** data source
- Use TraceQL to query traces

## Querying Traces

### TraceQL Examples

Find all traces for a specific conversation:
```
{ span.gen_ai.conversation_id = "a24ea2c1-fd51-4354-af5e-f5f8ab9e3bcf" }
```

Find tool execution spans:
```
{ span.gen_ai.operation.name = "tool_call" }
```

Find traces from the backend service:
```
{ resource.service.name = "agent-api" }
```

Find slow traces (>5 seconds):
```
{ duration > 5s }
```

Combine conditions:
```
{ span.gen_ai.operation.name = "tool_call" && duration > 1s }
```

### Key Trace Attributes

| Attribute | Description |
|-----------|-------------|
| `gen_ai.conversation_id` | CopilotKit thread ID for correlating all requests in a conversation |
| `gen_ai.operation.name` | Operation type (chat, tool_call, etc.) |
| `gen_ai.request.model` | LLM model used |
| `gen_ai.response.finish_reasons` | How the LLM response completed |
| `service.name` | Service identifier (agent-api, mcp-server, etc.) |

## Services

| Service | Port | Description |
|---------|------|-------------|
| Grafana | 3001 | Visualization UI |
| Tempo | 3200 | Trace storage HTTP API |
| OTEL Collector | 4317 | OTLP gRPC receiver |
| OTEL Collector | 4318 | OTLP HTTP receiver |

## Management Commands

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f tempo

# Stop all services
docker compose down

# Stop and remove volumes (clear all data)
docker compose down -v

# Restart a specific service
docker compose restart tempo
```

## Troubleshooting

### No traces appearing in Grafana

1. Verify the backend is configured correctly:
   ```bash
   # Check backend environment
   grep OTEL backend/.env
   ```

2. Check the collector is receiving traces:
   ```bash
   docker compose logs otel-collector
   ```

3. Verify Tempo is healthy:
   ```bash
   curl http://localhost:3200/ready
   ```

### Connection refused to OTLP endpoint

If running the backend outside Docker:
- Use `localhost:4317` for gRPC
- Use `localhost:4318` for HTTP

If running the backend inside Docker:
- Use `otel-collector:4317` for gRPC
- Use `otel-collector:4318` for HTTP

### Traces not correlating by conversation

Ensure the `conversation_id_injection` patch is enabled in the backend. Check that `gen_ai.conversation_id` appears in trace attributes.

## Data Retention

By default, traces are retained for 48 hours. To change this, edit `tempo-config.yaml`:

```yaml
compactor:
  compaction:
    block_retention: 168h  # 7 days
```

Then restart Tempo:
```bash
docker compose restart tempo
```
