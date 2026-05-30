from __future__ import annotations

# Canonical trace identity attributes
ATTR_CONVERSATION_ID = "gen_ai.conversation.id"
ATTR_TURN_ID = "gen_ai.turn.id"
ATTR_RUN_ID = "gen_ai.run.id"
ATTR_TOOL_CALL_ID = "gen_ai.tool.call.id"
ATTR_A2A_INTERACTION_ID = "gen_ai.a2a.interaction.id"

# Tool attributes
ATTR_TOOL_NAME = "gen_ai.tool.name"
ATTR_TOOL_STATUS = "gen_ai.tool.status"

# A2A attributes
ATTR_A2A_SOURCE_AGENT = "gen_ai.a2a.source_agent"
ATTR_A2A_TARGET_AGENT = "gen_ai.a2a.target_agent"
ATTR_A2A_OPERATION = "gen_ai.a2a.operation"
ATTR_A2A_STATUS = "gen_ai.a2a.status"

TRACE_IDENTITY_HEADER_MAP = {
    ATTR_CONVERSATION_ID: "x-trace-conversation-id",
    ATTR_TURN_ID: "x-trace-turn-id",
    ATTR_RUN_ID: "x-trace-run-id",
    ATTR_TOOL_CALL_ID: "x-trace-tool-call-id",
    ATTR_A2A_INTERACTION_ID: "x-trace-a2a-interaction-id",
}
