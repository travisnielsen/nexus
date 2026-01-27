"""
Patch 3: AG-UI Event Stream Fix

The agent-framework-ag-ui library has several issues when used with CopilotKit:

1. TEXT_MESSAGE_START is emitted before tool calls, but if a tool call interrupts,
   the message is never closed, causing "Cannot send 'RUN_FINISHED' while text 
   messages are still active" errors.

2. Duplicate tool calls are sometimes sent with different IDs.

3. MESSAGES_SNAPSHOT at the end of streams can cause CopilotKit to rebuild
   its message state and lose tool card renders.

This patch wraps AgentFrameworkAgent.run_agent to:
- Buffer TEXT_MESSAGE_START until actual content arrives
- Discard buffered messages interrupted by tool calls
- Deduplicate tool calls by name within the same request
- Suppress MESSAGES_SNAPSHOT events
- Inject missing TEXT_MESSAGE_END events before RUN_FINISHED

STATUS: Confirmed needed for both Assistants API and Responses API.
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
    """Patch AgentFrameworkAgent.run_agent to fix event stream issues.
    
    This patch applies to both Assistants API and Responses API.
    
    Returns:
        True if patch was applied, False otherwise.
    """
    try:
        from agent_framework_ag_ui._agent import AgentFrameworkAgent
        from ag_ui.core import (
            TextMessageEndEvent,
            EventType,
        )
        
        # Import ContextVar to set filter at request start
        from agents.utils import current_active_filter
        
        # Import thread ID ContextVar for Responses API middleware
        from middleware.responses_api import get_current_agui_thread_id
        
        _original_run_agent = AgentFrameworkAgent.run_agent
        
        async def patched_run_agent(self, input_data: dict):
            """Wrapped run_agent that:
            1. Sets AG-UI thread_id ContextVar for ResponsesApiThreadMiddleware
            2. Syncs activeFilter from CopilotKit context to ContextVar for analyze_flights
            3. Buffers TEXT_MESSAGE_START to avoid orphaned messages
            4. Deduplicates tool calls
            5. Suppresses MESSAGES_SNAPSHOT
            6. Injects missing TextMessageEndEvent before RunFinishedEvent
            """
            # ===================================================================
            # CRITICAL: Extract thread_id from CopilotKit/AG-UI and set ContextVar
            # This enables ResponsesApiThreadMiddleware to map thread→response_id
            # The Responses API uses response_id chains for conversation continuity.
            # Each LLM call: pass previous response_id → get new response_id.
            # ===================================================================
            # Log full input_data for debugging
            logger.debug("[AGUI-PATCH] Full input_data dump: %s", json.dumps(input_data, default=str)[:2000])
            
            # First, check context for threadId (workaround for CopilotKit not passing to HttpAgent)
            # We need to parse context FIRST before using it for thread_id
            context_list = input_data.get("context", [])
            context_thread_id = None  # Will be extracted from context if present
            
            if context_list:
                logger.debug("[AGUI-PATCH] Context present: %s items", len(context_list))
                # Find the dashboard state context
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
            
            # Now determine thread_id, preferring context_thread_id if available
            # Priority: context (useCopilotReadable) > forwardedProps > state > input_data direct > fallback UUID
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
                    # Set conversation_id attribute for Azure Foundry correlation
                    # Azure Foundry looks for 'gen_ai.conversation.id' or 'conversation_id'
                    current_span.set_attribute("gen_ai.conversation.id", thread_id)
                    current_span.set_attribute("conversation_id", thread_id)
                    logger.debug("[AGUI-PATCH] Set span attribute gen_ai.conversation.id: %s", thread_id)
            
            # Log incoming data for debugging
            flights = state.get("flights", [])
            active_filter = state.get("activeFilter")
            
            # Check for readable context (may be in different locations)
            if "readables" in input_data:
                logger.debug("[AGUI-PATCH] Readables present: %s", input_data.get("readables"))
            if "frontend_context" in state:
                logger.debug("[AGUI-PATCH] State.frontend_context: %s", state.get("frontend_context"))
            
            # Log state info
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
            
            # ================================================================
            # EVENT BUFFERING STRATEGY
            # ================================================================
            # The Assistants API often sends TEXT_MESSAGE_START immediately
            # before tool calls. If we emit START immediately, CopilotKit shows
            # a spinner, but when tools interrupt, closing the orphan message
            # causes "Cannot send 'RUN_FINISHED' while text messages are still active".
            # 
            # Strategy:
            # - Buffer TEXT_MESSAGE_START until we see actual content OR run ends
            # - If tools interrupt a buffered message, discard it (no spinner shown)
            # - If content arrives, emit the buffered START + content
            # - This avoids orphaned messages that break CopilotKit state
            # ================================================================
            
            pending_text_start = None  # Buffered TEXT_MESSAGE_START (waiting for content)
            emitted_messages: set[str] = set()  # Messages we've sent START for
            messages_with_content: set[str] = set()  # Messages that received TEXT_MESSAGE_CONTENT
            emitted_tool_calls: set[str] = set()  # Tool call IDs we've already emitted
            emitted_tool_names: set[str] = set()  # Tool names we've already emitted (catches dupes with different IDs)
            suppressed_tool_ids: set[str] = set()  # Tool call IDs we're suppressing
            event_count = 0
            suppressed_count = 0
            emitted_count = 0  # Track how many events we actually yield
            
            logger.debug("[AGUI-PATCH] === Starting event stream ===")
            
            async for event in _original_run_agent(self, input_data):
                event_count += 1
                event_type = getattr(event, "type", None)
                event_name = str(event_type).replace("EventType.", "") if event_type else "UNKNOWN"
                
                # Extract message_id for logging
                msg_id = getattr(event, "message_id", None)
                tool_call_id = getattr(event, "tool_call_id", None)
                
                # Log EVERY incoming event
                logger.debug(f"[AGUI-PATCH] IN  #{event_count}: {event_name} (msg={msg_id}, tool={tool_call_id})")
                
                # Handle TEXT_MESSAGE_START - buffer it, don't emit yet
                if event_type == EventType.TEXT_MESSAGE_START:
                    # Discard any previous pending start (shouldn't happen but be safe)
                    if pending_text_start:
                        old_id = getattr(pending_text_start, "message_id", None)
                        logger.warning(f"[AGUI-PATCH] Discarding orphaned TEXT_MESSAGE_START: {old_id}")
                        suppressed_count += 1
                    # Buffer this new start event
                    pending_text_start = event
                    logger.debug(f"[AGUI-PATCH] BUFFERED TEXT_MESSAGE_START: {msg_id}")
                    continue  # Don't yield yet
                
                # Handle TEXT_MESSAGE_CONTENT - emit buffered start first if present
                elif event_type == EventType.TEXT_MESSAGE_CONTENT:
                    # If we have a pending start for this message, emit it first
                    if pending_text_start:
                        pending_id = getattr(pending_text_start, "message_id", None)
                        if pending_id == msg_id:
                            emitted_count += 1
                            logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TEXT_MESSAGE_START (msg={pending_id})")
                            yield pending_text_start
                            emitted_messages.add(pending_id)
                            pending_text_start = None
                    
                    # Track that this message has content
                    if msg_id:
                        messages_with_content.add(msg_id)
                    
                    emitted_count += 1
                    content = getattr(event, "delta", "")[:50] if hasattr(event, "delta") else ""
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TEXT_MESSAGE_CONTENT (msg={msg_id}, content='{content}...')")
                    yield event
                    continue
                
                # Handle TEXT_MESSAGE_END
                elif event_type == EventType.TEXT_MESSAGE_END:
                    # Only emit END if we actually emitted START for this message
                    if msg_id in emitted_messages:
                        emitted_count += 1
                        logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TEXT_MESSAGE_END (msg={msg_id})")
                        yield event
                        emitted_messages.discard(msg_id)
                    else:
                        logger.warning(f"[AGUI-PATCH] SUPPRESSED TEXT_MESSAGE_END for non-emitted message: {msg_id}")
                        suppressed_count += 1
                    continue
                
                # Handle TOOL_CALL_START - discard any pending text message and dedupe
                elif event_type == EventType.TOOL_CALL_START:
                    # Discard any pending text that was interrupted by this tool call
                    if pending_text_start:
                        old_id = getattr(pending_text_start, "message_id", None)
                        logger.warning(f"[AGUI-PATCH] Tool call interrupted text message, discarding: {old_id}")
                        suppressed_count += 1
                        pending_text_start = None
                    
                    # Get tool call info for logging and deduplication
                    tool_name = getattr(event, "tool_call_name", "unknown")
                    tool_call_id = getattr(event, "tool_call_id", None)
                    
                    # Deduplicate by tool_call_id - if we've seen this exact ID, skip it
                    if tool_call_id and tool_call_id in emitted_tool_calls:
                        logger.warning(f"[AGUI-PATCH] SUPPRESSED DUPLICATE tool call by ID: {tool_name} (id={tool_call_id})")
                        suppressed_count += 1
                        suppressed_tool_ids.add(tool_call_id)
                        continue  # Skip this duplicate
                    
                    # Also dedupe by tool name within same request (different IDs, same logical call)
                    # This catches cases where Azure sends the same tool call with different IDs
                    if tool_name in emitted_tool_names:
                        logger.warning(f"[AGUI-PATCH] SUPPRESSED DUPLICATE tool call by NAME: {tool_name} (id={tool_call_id})")
                        suppressed_count += 1
                        if tool_call_id:
                            suppressed_tool_ids.add(tool_call_id)
                        continue  # Skip this duplicate
                    
                    # Track both the ID and the name
                    if tool_call_id:
                        emitted_tool_calls.add(tool_call_id)
                    emitted_tool_names.add(tool_name)
                    
                    emitted_count += 1
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TOOL_CALL_START - {tool_name} (id={tool_call_id})")
                    yield event
                    continue
                
                # Handle TOOL_CALL_ARGS - suppress if tool was deduplicated
                elif event_type == EventType.TOOL_CALL_ARGS:
                    tool_call_id = getattr(event, "tool_call_id", None)
                    
                    if tool_call_id and tool_call_id in suppressed_tool_ids:
                        logger.warning(f"[AGUI-PATCH] SUPPRESSED TOOL_CALL_ARGS for duplicate: {tool_call_id}")
                        suppressed_count += 1
                        continue  # Skip this args event
                    
                    emitted_count += 1
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TOOL_CALL_ARGS (tool={tool_call_id})")
                    yield event
                    continue
                
                # Handle TOOL_CALL_END - suppress if tool was deduplicated
                elif event_type == EventType.TOOL_CALL_END:
                    tool_call_id = getattr(event, "tool_call_id", None)
                    
                    if tool_call_id and tool_call_id in suppressed_tool_ids:
                        logger.warning(f"[AGUI-PATCH] SUPPRESSED TOOL_CALL_END for duplicate: {tool_call_id}")
                        suppressed_count += 1
                        continue  # Skip this end event (keep in suppressed set for RESULT)
                    
                    emitted_count += 1
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TOOL_CALL_END (tool={tool_call_id})")
                    yield event
                    continue
                
                # Handle TOOL_CALL_RESULT - suppress if tool was deduplicated
                elif event_type == EventType.TOOL_CALL_RESULT:
                    tool_call_id = getattr(event, "tool_call_id", None)
                    
                    if tool_call_id and tool_call_id in suppressed_tool_ids:
                        logger.warning(f"[AGUI-PATCH] SUPPRESSED TOOL_CALL_RESULT for duplicate: {tool_call_id}")
                        suppressed_count += 1
                        suppressed_tool_ids.discard(tool_call_id)
                        continue  # Skip this result event
                    
                    emitted_count += 1
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TOOL_CALL_RESULT (tool={tool_call_id})")
                    yield event
                    continue
                
                # Handle RUN_FINISHED
                elif event_type == EventType.RUN_FINISHED:
                    # Discard any pending text start that never got content
                    if pending_text_start:
                        old_id = getattr(pending_text_start, "message_id", None)
                        logger.warning(f"[AGUI-PATCH] Discarding pending text at run end: {old_id}")
                        suppressed_count += 1
                        pending_text_start = None
                    
                    # Inject END events for any messages we emitted but didn't close
                    for open_msg_id in list(emitted_messages):
                        if open_msg_id in messages_with_content:
                            emitted_count += 1
                            logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: TEXT_MESSAGE_END (injected for {open_msg_id})")
                            yield TextMessageEndEvent(message_id=open_msg_id)
                    
                    emitted_messages.clear()
                    messages_with_content.clear()
                    emitted_tool_calls.clear()
                    emitted_tool_names.clear()
                    suppressed_tool_ids.clear()
                    
                    emitted_count += 1
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: RUN_FINISHED")
                    logger.debug(f"[AGUI-PATCH] === Stream complete: {event_count} IN, {emitted_count} OUT, {suppressed_count} suppressed ===")
                    yield event
                    continue
                
                # Handle MESSAGES_SNAPSHOT - suppress it as it may cause CopilotKit to rebuild message state
                # and lose tool call renders
                elif event_type == EventType.MESSAGES_SNAPSHOT:
                    logger.warning(f"[AGUI-PATCH] SUPPRESSED MESSAGES_SNAPSHOT (may cause tool card disappearance)")
                    suppressed_count += 1
                    continue
                
                # All other events pass through
                else:
                    emitted_count += 1
                    logger.debug(f"[AGUI-PATCH] OUT #{emitted_count}: {event_name}")
                    yield event
        
        # Replace the method on the class
        AgentFrameworkAgent.run_agent = patched_run_agent
        
        logger.debug("Applied AG-UI event stream patch (patched AgentFrameworkAgent.run_agent)")
        return True
        
    except ImportError as e:
        logger.warning("Failed to apply AG-UI event stream patch: %s", e)
        return False
