# US1 Turn/Tool Validation

## Procedure

1. Run multi-turn conversation with at least two tool calls in one turn.
2. Query traces for turn/run identifiers.
3. Confirm every tool call span links to the originating run/turn identifiers.

## Evidence

- Use src/backend/logistics/scripts/validate_turn_traces.py output.
- Attach screenshots from Foundry V2 portal trace view.
