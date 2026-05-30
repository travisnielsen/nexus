# Telemetry Baseline Inventory

## Services

- Frontend CopilotKit proxy: src/frontend/src/app/api/copilotkit/[[...path]]/route.ts
- Backend AG-UI endpoint: src/backend/logistics/main.py (/logistics)
- Tool execution modules: src/backend/logistics/agents/tools/*.py
- A2A receiver: src/backend/recommendations/main.py

## Span Sources

- FastAPI request spans
- Agent framework orchestration spans
- Tool spans (filter/analysis/chart/recommendations)
- A2A outbound/inbound spans

## Correlation Keys

- gen_ai.conversation.id
- gen_ai.turn.id
- gen_ai.run.id
- gen_ai.tool.call.id
- gen_ai.a2a.interaction.id
