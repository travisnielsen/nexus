---
name: agent-tracer
description: Investigate a multi-agent / LLM chat conversation end-to-end by querying Application Insights (or Log Analytics) for traces, dependencies, exceptions, and custom events tied to a specific conversation, thread, or session identifier. Use when the user asks to "trace", "debug", "analyze", or "explain" a conversation, when comparing what an agent trajectory / orchestrator UI shows vs. what actually executed, when diagnosing missing agent spans, or when investigating latency, tool calls, retrieval behavior, validation failures, or routing decisions. Triggers on conversation/thread/session IDs (e.g. `conv_*`, `thread_*`, `sess_*`), IDs from screenshots/traces, or any "why did/didn't X happen in this conversation" question.
---

# Agent Tracer

Pull the full execution story of an agent conversation out of Application Insights and reconstruct what the backend actually did — including pieces that an orchestrator's built-in trajectory UI may hide.

## When to Use

- User pastes a conversation / thread / session ID and asks what happened.
- A span is missing from the trajectory UI (e.g. "I don't see agent X").
- Latency in the UI doesn't match span durations.
- A downstream call (DB query, vector search, HTTP call, validation) needs to be traced.
- Comparing two execution paths (e.g. fast-path vs LLM fallback, cached vs uncached).

## Inputs You Need

1. **Conversation identifier** — required. Extract from the user's message or screenshot if not provided as plain text.
2. **Application Insights / Log Analytics resource** — discover automatically (see step 1 below). Do not ask the user unless discovery fails.
3. **Optional**: time window (default last 24h), turn number, focus area (latency / errors / routing / specific agent).

## Workflow

### 1. Discover the telemetry backend

Look in the project for a connection string or instrumentation key. Common locations:

- `.env`, `.env.local`, `.env.<stage>` at repo root or under `src/`, `backend/`, `app/`, `api/`
- `appsettings.json`, `appsettings.*.json`
- `local.settings.json` (Azure Functions)
- `azure.yaml` / `.azure/<env>/.env` (azd)
- Terraform/Bicep outputs in `infra/`

Extract whichever is present:

```bash
# Connection string (preferred)
grep -RhoE "APPLICATIONINSIGHTS_CONNECTION_STRING=[^[:space:]\"']+" . 2>/dev/null | head -1

# Or just the instrumentation key
grep -RhoE "InstrumentationKey=[a-f0-9-]+" . 2>/dev/null | head -1
```

Resolve the resource via Azure Resource Graph (`azure_resources-query_azure_resource_graph`):

> find the Application Insights component with InstrumentationKey `<key>` and return its name, resourceGroup, subscriptionId, and workspaceResourceId across all subscriptions

If the by-key lookup returns 0 records (Resource Graph doesn't always project `InstrumentationKey`), fall back to listing all `microsoft.insights/components` and pick the one matching the project's naming convention. Sibling Log Analytics workspaces typically share a prefix and live in the same resource group.

Cache `{ subscription, resource_group, workspace_name, app_insights_name }` for the session — do not repeat discovery per query.

### 2. Locate the conversation's spans

Use `mcp_azure_mcp_monitor` → `monitor_workspace_log_query`. Conversation IDs are typically emitted in one of:

- `AppDependencies.Properties` (custom dimensions on agent spans)
- `AppTraces.Message` (structured log lines)
- `AppRequests.OperationName` or `Properties`
- A dedicated custom event in `AppEvents` or a custom table

Start with a broad sweep that doesn't assume a column:

```kusto
union AppTraces, AppDependencies, AppRequests, AppExceptions, AppEvents
| where TimeGenerated > ago(24h)
| where Properties contains "<conv_id>"
   or Message contains "<conv_id>"
   or OperationName contains "<conv_id>"
   or Name contains "<conv_id>"
| project TimeGenerated, ItemType=Type, Name, OperationName,
          Message=substring(tostring(Message),0,200),
          DurationMs, OperationId, ParentId, Id
| order by TimeGenerated asc
| take 200
```

Record the **OperationIds** that surface — those are your trace anchors.

### 3. Fill in the non-span gap

Trajectory/orchestrator UIs usually render only LLM/agent dependency spans. Plain application logs (validation, DB execution, cache hits, retries) frequently log via the standard logger and end up in `AppTraces` with `OperationId = 0…0` (no span context). To see them, query by the **time window** spanning the conversation:

```kusto
union AppTraces, AppDependencies
| where TimeGenerated between (datetime(<start>) .. datetime(<end>))
| project TimeGenerated, ItemType=Type, Name, Target,
          DurationMs, Message=substring(tostring(Message),0,220)
| order by TimeGenerated asc
| take 500
```

Use the first/last timestamps from step 2 as bounds, padded by ±2 seconds.

### 4. Interpret the timeline

For each event, classify it as one of:

| Category               | Typical signals                                                              |
| ---------------------- | ---------------------------------------------------------------------------- |
| Agent / LLM invocation | `invoke_agent <name>`, `chat <model>`, `gen_ai.*` attributes                 |
| Tool / function call   | `execute_tool <name>`, custom span names                                     |
| Retrieval              | `SearchClient.*`, `*.embeddings`, vector DB HTTP calls                       |
| Data plane             | SQL/ODBC spans, `*.cosmos`, `*.storage`, HTTP dependencies                   |
| Auth / infra           | `GET /msi/token`, identity endpoints — usually noise unless investigating    |
| Application logic      | `AppTraces` with `OperationId=0…0` — module logger output                    |
| Errors                 | `AppExceptions`, traces with `SeverityLevel >= 3`                            |

Then map them back to source code by symbol name. Useful searches:

- `grep_search` for the span/log message text in the repo to find the emitting file.
- For OpenTelemetry: span names usually match function names or are set explicitly in `tracer.start_as_current_span("…")`.

### 5. Reconstruct routing / branching decisions

Common diagnostic patterns:

- **Missing agent span** → either (a) a deterministic / cached path short-circuited before the LLM call, so no `invoke_agent` was emitted, or (b) a different branch was taken. Confirm by searching `AppTraces` for log lines around the decision point ("skipping LLM", "cache hit", "fallback to …", "score=… threshold=…").
- **Wall-clock vs span sum mismatch** → non-instrumented work (DB execution, post-processing, streaming) is the delta. Don't blame an agent without checking application logs in the same window.
- **Duplicate `<name>:1`, `<name>:2` spans** → some frameworks emit suffixed spans for nested calls within the same agent run. Not necessarily a retry.
- **Long gap between spans** → look for `AppTraces` and `AppDependencies` in the gap; this is where uninstrumented code is hiding.

## MCP Tools to Use

| Tool                                                      | Purpose                                                       |
| --------------------------------------------------------- | ------------------------------------------------------------- |
| `azure_resources-query_azure_resource_graph`              | Resolve App Insights component + Log Analytics workspace.     |
| `mcp_azure_mcp_monitor` / `monitor_workspace_log_query`   | Run KQL against the workspace (primary tool).                 |
| `mcp_azure_mcp_monitor` / `monitor_resource_log_query`    | When telemetry is scoped to one resource.                     |
| `mcp_azure_mcp_applicationinsights`                       | List components when Resource Graph projection is incomplete. |
| `mcp_azure_mcp_kusto`                                     | Only if telemetry is exported to ADX.                         |

Prefer `monitor_workspace_log_query` — most applications log workspace-wide via diagnostic settings.

## Reusable KQL Snippets

Substitute `<conv_id>` with the conversation identifier.

### Full timeline grouped by operation

```kusto
let convId = "<conv_id>";
let opIds = toscalar(
    union AppTraces, AppDependencies, AppRequests
    | where TimeGenerated > ago(24h)
    | where Message contains convId or Properties contains convId or OperationName contains convId
    | summarize make_set(OperationId)
);
union AppTraces, AppDependencies, AppExceptions, AppRequests
| where TimeGenerated > ago(24h)
| where OperationId in (opIds) or Message contains convId or Properties contains convId
| project TimeGenerated, Type, Name, DurationMs,
          Message=substring(tostring(Message),0,200)
| order by TimeGenerated asc
```

### Per-span latency breakdown

```kusto
AppDependencies
| where TimeGenerated > ago(24h)
| where Properties has "<conv_id>"
| summarize Count=count(), TotalMs=sum(DurationMs), MaxMs=max(DurationMs) by Name
| order by TotalMs desc
```

### Exceptions tied to the conversation

```kusto
let convId = "<conv_id>";
AppExceptions
| where TimeGenerated > ago(24h)
| where OperationId in ((
    union AppTraces, AppDependencies
    | where Message contains convId or Properties contains convId
    | distinct OperationId))
| project TimeGenerated, ProblemId, OuterMessage, Method, OperationId
```

### Distinct span/log sources in a window

```kusto
union AppTraces, AppDependencies
| where TimeGenerated between (datetime(<start>) .. datetime(<end>))
| summarize Count=count(), TotalMs=sum(DurationMs) by Type, Name
| order by Count desc
```

## Pitfalls

- **`OperationId = 00000000…`** on `AppTraces` is normal for module-level `logger.info(...)` outside an active span. Don't treat as orphaned — correlate by time window.
- **Auth / token noise** (`GET /msi/token`, IMDS calls, OAuth endpoints) is common and rarely interesting.
- **Dependency `DurationMs = 0`** often means the wrapper span doesn't time the child; the real timing is on a nested HTTP/SDK call.
- **`Message` is empty on `AppDependencies`** — filter by `Properties` or `Name` instead.
- **Custom dimensions are in `Properties`** as a JSON-like string; use `parse_json(Properties)` or `Properties has "<key>"` for filtering.
- **Trajectory UIs are not the source of truth** — they typically filter to agent/LLM spans only. Always cross-check against the raw telemetry for the full picture.
- **Sampling** — if Application Insights adaptive sampling is enabled, some spans/traces may be absent. Check `itemCount` or `samplingDecision` if a known event is missing.

## Output Format

Structure findings back to the user as:

1. **One-line summary** — which path did the conversation take?
2. **Per-turn timeline** — bullet list with timestamps, span names, durations.
3. **Key decisions** — routing scores, thresholds, cache hits, fallbacks — quoted from `AppTraces`.
4. **Explanation of any missing span** the user asked about, citing the log line(s) that prove the short-circuit.
5. **(Optional)** Remediation — e.g. wrap the missing code path in a manual OpenTelemetry span so it appears in the trajectory.