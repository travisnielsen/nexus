"""
Patch: AG-UI Context Synchronization

This patch wraps AgentFrameworkAgent.run_agent to:
1. Extract CopilotKit threadId and set ContextVar for ResponsesApiThreadMiddleware
2. Sync activeFilter from CopilotKit context to ContextVar for analyze_flights
3. Set OpenTelemetry conversation_id span attribute for tracing correlation

HISTORY:
  Previous versions of this patch also buffered TEXT_MESSAGE_START events,
  deduplicated tool calls, suppressed MESSAGES_SNAPSHOT, and injected missing
  TEXT_MESSAGE_END events. These workarounds were removed after upgrading to
  agent-framework >= 1.0.0b260210 which incorporates fixes from PR #3635:
    - #3568: TextMessageEndEvent now emitted after tool results
    - #3619: MessagesSnapshot separates tool_calls and content properly
    - MCP tool double-call bug fixed

STATUS: Required for project-specific context synchronization.
"""

from __future__ import annotations

import json
import logging
import uuid

# OpenTelemetry for setting conversation_id span attribute
try:
    from opentelemetry import trace, baggage, context as otel_context
    from opentelemetry.trace import SpanKind
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    trace = None  # type: ignore
    baggage = None  # type: ignore
    otel_context = None  # type: ignore
    SpanKind = None  # type: ignore

logger = logging.getLogger(__name__)

# Tracer for creating conversation spans
_tracer = None

def _get_tracer():
    """Get or create the tracer for conversation tracking."""
    global _tracer
    if _tracer is None and HAS_OTEL:
        _tracer = trace.get_tracer("logistics-agent", "1.0.0")
    return _tracer


def apply_agui_event_stream_patch() -> bool:
    """Patch AgentFrameworkAgent.run_agent to sync context from CopilotKit.
    
    This patch applies project-specific context synchronization:
    - Extracts threadId from CopilotKit context for ResponsesApiThreadMiddleware
    - Syncs activeFilter from CopilotKit context to ContextVar for analyze_flights
    - Sets OpenTelemetry conversation_id for tracing correlation
    
    Event stream workarounds (buffering, dedup, snapshot suppression) have been
    removed — agent-framework >= 1.0.0b260210 fixes these natively (PR #3635).
    
    Returns:
        True if patch was applied, False otherwise.
    """
    try:
        from agent_framework_ag_ui._agent import AgentFrameworkAgent
        
        # Import ContextVar to set filter at request start
        from agents.utils import current_active_filter
        
        # Import thread ID ContextVar for Responses API middleware
        from middleware.responses_api import get_current_agui_thread_id
        
        _original_run_agent = AgentFrameworkAgent.run_agent
        
        async def patched_run_agent(self, input_data: dict):
            """Wrapped run_agent that:
            1. Sets AG-UI thread_id ContextVar for ResponsesApiThreadMiddleware
            2. Syncs activeFilter from CopilotKit context to ContextVar for analyze_flights
            3. Sets OpenTelemetry conversation_id span attribute for tracing
            
            The event stream is passed through unmodified — framework fixes in
            agent-framework >= 1.0.0b260210 handle TEXT_MESSAGE_END, MESSAGES_SNAPSHOT,
            and tool call deduplication natively.
            """
            # ===================================================================
            # CRITICAL: Extract thread_id from CopilotKit/AG-UI and set ContextVar
            # This enables ResponsesApiThreadMiddleware to map thread→response_id
            # The Responses API uses response_id chains for conversation continuity.
            # Each LLM call: pass previous response_id → get new response_id.
            # ===================================================================
            logger.debug("[AGUI-PATCH] Full input_data dump: %s", json.dumps(input_data, default=str)[:2000])
            
            # Parse context list for threadId and activeFilter
            context_list = input_data.get("context", [])
            context_thread_id = None
            
            if context_list:
                logger.debug("[AGUI-PATCH] Context present: %s items", len(context_list))
                for ctx_item in context_list:
                    if isinstance(ctx_item, dict) and "value" in ctx_item:
                        try:
                            ctx_value = json.loads(ctx_item["value"])
                            
                            # Extract threadId from context (workaround for CopilotKit not passing to HttpAgent)
                            if "threadId" in ctx_value and ctx_value["threadId"]:
                                context_thread_id = ctx_value["threadId"]
                                logger.debug("[AGUI-PATCH] Found threadId in context: %s", context_thread_id)
                            
                            if "activeFilter" in ctx_value:
                                # Extract the filter and sync to ContextVar
                                filter_data = ctx_value["activeFilter"]
                                synced_filter = {
                                    "routeFrom": filter_data.get("routeFrom"),
                                    "routeTo": filter_data.get("routeTo"),
                                    "utilizationType": filter_data.get("utilizationType"),
                                    "riskLevel": filter_data.get("riskLevel"),
                                }
                                current_active_filter.set(synced_filter)
                                logger.debug("[AGUI-PATCH] Synced activeFilter to ContextVar: %s", synced_filter)
                        except (json.JSONDecodeError, TypeError) as e:
                            logger.warning("[AGUI-PATCH] Failed to parse context value: %s", e)
            else:
                logger.debug("[AGUI-PATCH] No context in input_data")
            
            # Determine thread_id with priority chain
            forwarded_props = input_data.get("forwardedProps", {})
            state = input_data.get("state", {})
            
            thread_id = (
                context_thread_id or  # HIGHEST PRIORITY: from useCopilotReadable context
                input_data.get("thread_id") or 
                input_data.get("threadId") or
                forwarded_props.get("threadId") or
                state.get("threadId") or
                str(uuid.uuid4())  # Fallback if not provided
            )
            
            # Determine source for logging
            if context_thread_id:
                source = "CONTEXT (useCopilotReadable)"
            elif input_data.get("thread_id") or input_data.get("threadId"):
                source = "input_data"
            elif forwarded_props.get("threadId"):
                source = "forwardedProps"
            elif state.get("threadId"):
                source = "state"
            else:
                source = "FALLBACK UUID (NEW)"
            
            get_current_agui_thread_id().set(thread_id)
            logger.debug("[AGUI-PATCH] Set thread_id ContextVar: %s (source: %s)", thread_id, source)
            
            # ===================================================================
            # CRITICAL: Set conversation_id as OpenTelemetry span attribute
            # This enables Azure Foundry to display the Conversation ID in traces
            # The attribute name follows OpenTelemetry GenAI semantic conventions
            # ===================================================================
            if HAS_OTEL:
                current_span = trace.get_current_span()
                if current_span and current_span.is_recording():
                    current_span.set_attribute("gen_ai.conversation.id", thread_id)
                    current_span.set_attribute("conversation_id", thread_id)
                    logger.debug("[AGUI-PATCH] Set span attribute gen_ai.conversation.id: %s", thread_id)
            
            # Log incoming state for debugging
            flights = state.get("flights", [])
            active_filter = state.get("activeFilter")
            
            if active_filter:
                is_cleared = (
                    not active_filter.get("routeFrom") and
                    not active_filter.get("routeTo") and
                    not active_filter.get("utilizationType") and
                    not active_filter.get("riskLevel")
                )
                if is_cleared:
                    logger.debug("[AGUI-PATCH] Incoming state: filters CLEARED (all nulls)")
                else:
                    logger.debug("[AGUI-PATCH] Incoming state: activeFilter=%s", active_filter)
            else:
                logger.debug("[AGUI-PATCH] Incoming state: no activeFilter")
            
            logger.debug("[AGUI-PATCH] Full incoming state: flights=%d, activeFilter=%s", len(flights), active_filter)
            
            # ===================================================================
            # PASS THROUGH EVENT STREAM
            # Framework fixes in agent-framework >= 1.0.0b260210 (PR #3635)
            # handle TEXT_MESSAGE_END, MESSAGES_SNAPSHOT, and tool dedup natively.
            # No event interception needed.
            # ===================================================================
            async for event in _original_run_agent(self, input_data):
                yield event
        
        # Replace the method on the class
        AgentFrameworkAgent.run_agent = patched_run_agent
        
        logger.debug("Applied AG-UI context sync patch (patched AgentFrameworkAgent.run_agent)")
        return True
        
    except ImportError as e:
        logger.warning("Failed to apply AG-UI context sync patch: %s", e)
        return False
