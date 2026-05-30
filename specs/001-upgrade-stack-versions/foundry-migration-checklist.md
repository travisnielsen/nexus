# Foundry Client Migration Checklist

Created: 2026-05-29

## Migration Goal

Migrate backend chat client usage to Foundry-native `FoundryChatClient` while preserving existing agent behavior.

## Checklist

- [X] Confirm authoritative docs/source for `FoundryChatClient` and current support status.
- [X] Update `src/backend/logistics/clients.py` to use `agent_framework.foundry.FoundryChatClient`.
- [X] Preserve return contract as `SupportsChatGetResponse`.
- [X] Preserve async credential flow (`azure.identity.aio`).
- [X] Maintain `create_logistics_agent` behavior and tool registration semantics.
- [ ] Validate AG-UI/CopilotKit compatibility after migration.
- [ ] Record behavior deltas (if any) and mitigations.
