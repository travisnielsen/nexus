# Baseline KQL Pack

## Turn Trace Presence

```kql
AppDependencies
| where TimeGenerated > ago(24h)
| where Name has "invoke_agent" or Name has "run"
| summarize turns=count()
```

## Tool Trace Presence

```kql
AppDependencies
| where TimeGenerated > ago(24h)
| where Name has "tool" or tostring(Properties["gen_ai.operation.name"]) == "execute_tool"
| summarize tools=count()
```

## A2A Trace Presence

```kql
AppDependencies
| where TimeGenerated > ago(24h)
| where Name has "a2a" or tostring(Properties["gen_ai.a2a.operation"]) != ""
| summarize a2a=count()
```
