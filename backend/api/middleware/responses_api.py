"""
Responses API Thread Middleware

This module provides middleware for managing Azure v2 Responses API conversation continuity.
It maps AG-UI client thread IDs to Azure response_id chains.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Callable, Awaitable
from collections.abc import AsyncIterable
import logging

from agent_framework._types import ChatResponse, ChatResponseUpdate, Content, Role
from agent_framework._middleware import ChatMiddleware, ChatContext

# OpenTelemetry for setting conversation_id span attribute
try:
    from opentelemetry import trace
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False


logger = logging.getLogger(__name__)


def _is_function_call(content: Content) -> bool:
    """Check if content is a function call."""
    return getattr(content, 'type', None) == 'function_call'


def _is_function_result(content: Content) -> bool:
    """Check if content is a function result."""
    return getattr(content, 'type', None) == 'function_result'


# Thread mapping store: maps AG-UI thread_id (client UUID) to Azure response_id
# This persists the response ID across requests so we can reuse Azure server-side state
_thread_response_store: dict[str, str] = {}

# ContextVar to pass AG-UI thread_id from orchestrator to middleware
# This allows the middleware to access the thread_id without modifying kwargs
_current_agui_thread_id: ContextVar[str | None] = ContextVar("current_agui_thread_id", default=None)

# ContextVar to signal that the response ended with a frontend-only tool call
# When this is True, we should NOT store the response_id because Azure is waiting
# for a tool result that will never come (frontend handles it locally)
_ended_with_frontend_tool: ContextVar[bool] = ContextVar("ended_with_frontend_tool", default=False)


# Frontend-only tools that are handled by CopilotKit, not the backend
# These tools don't send results back to Azure, so we shouldn't continue
# a conversation that ended with one of these tool calls
FRONTEND_ONLY_TOOLS = {
    "filter_dashboard",
    "setThemeColor",
    "display_flight_list",
    "display_flight_detail",
    "display_historical_chart",
}


def get_thread_response_store() -> dict[str, str]:
    """Get the thread-to-response-id mapping store."""
    return _thread_response_store


def get_current_agui_thread_id() -> ContextVar[str | None]:
    """Get the ContextVar for the current AG-UI thread ID."""
    return _current_agui_thread_id


def get_ended_with_frontend_tool() -> ContextVar[bool]:
    """Get the ContextVar for frontend tool detection."""
    return _ended_with_frontend_tool

class ResponsesApiThreadMiddleware(ChatMiddleware):
    """Chat middleware that manages response ID mapping for v2 Responses API.
    
    The Responses API uses response IDs (resp_*) for conversation continuity.
    AG-UI sends a client-generated thread_id (UUID), but we need to pass the
    previous response_id as the conversation_id to continue conversations.
    
    This middleware:
    1. Before request: Gets AG-UI thread_id from kwargs metadata and sets conversation_id to stored response_id
    2. After response: Stores the new response_id for the next request
    """
    
    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],  # noqa: A002 - required by base class
    ) -> None:
        """Process the chat request, managing response ID mapping."""
        # Get the AG-UI thread_id from ContextVar (set by AG-UI framework's orchestrator)
        agui_thread_id = _current_agui_thread_id.get()
        
        # Set conversation_id as OpenTelemetry span attribute for Azure Foundry tracing
        # This enables conversation correlation in Azure Foundry traces
        if agui_thread_id and HAS_OTEL:
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                current_span.set_attribute("gen_ai.conversation.id", agui_thread_id)
                current_span.set_attribute("conversation_id", agui_thread_id)
                logger.debug("[ResponsesApiThreadMiddleware] Set span attribute conversation_id: %s", agui_thread_id)
        
        # Log incoming messages for debugging
        logger.debug("[ResponsesApiThreadMiddleware] Incoming messages: %d", len(context.messages) if context.messages else 0)
        for i, msg in enumerate(context.messages or []):
            role = getattr(msg, 'role', 'unknown')
            contents_info = []
            if hasattr(msg, 'content') and msg.content:
                for c in (msg.content if isinstance(msg.content, list) else [msg.content]):
                    c_type = type(c).__name__
                    if hasattr(c, 'call_id'):
                        contents_info.append(f"{c_type}(call_id={c.call_id[:12] if c.call_id else None})")
                    elif hasattr(c, 'name'):
                        contents_info.append(f"{c_type}(name={c.name})")
                    else:
                        contents_info.append(c_type)
            logger.debug("[ResponsesApiThreadMiddleware]   msg[%d]: role=%s, contents=%s", i, role, contents_info)
        
        # Check if we have a stored response_id for this AG-UI thread
        if agui_thread_id and agui_thread_id in _thread_response_store:
            stored_response_id = _thread_response_store[agui_thread_id]
            logger.info("[ResponsesApiThreadMiddleware] CONTINUING thread %s with response_id %s", agui_thread_id, stored_response_id)
            # Set the conversation_id to the stored response_id
            # context.options is a dict in the new agent-framework API
            if context.options is None:
                context.options = {}
            context.options["conversation_id"] = stored_response_id
            
            # Filter messages to only send the last user message - server has the history via conversation_id
            # This prevents KeyError on call_id_to_id for tool calls from previous turns
            self._filter_messages_for_api(context)
        elif agui_thread_id:
            # First request for this thread OR we cleared the response_id (e.g., after frontend tool)
            # Still need to filter out tool-related messages that CopilotKit may have sent
            logger.info("[ResponsesApiThreadMiddleware] NEW/FRESH conversation for thread %s", agui_thread_id)
            if context.options is None:
                context.options = {}
            context.options["conversation_id"] = None
            
            # Filter out tool calls/results that would cause call_id_to_id errors
            # This removes TOOL messages and ASSISTANT messages with FunctionCallContent
            self._filter_messages_for_fresh_start(context)
        
        logger.debug("[ResponsesApiThreadMiddleware] After filtering: %d messages", len(context.messages) if context.messages else 0)
        
        # Call the next middleware/handler
        await next(context)
        
        # For streaming responses, capture the response_id after the stream completes
        if context.is_streaming and context.result is not None:
            if hasattr(context.result, '__aiter__'):
                # Wrap only to capture response_id
                # Type narrow: we've verified it's an AsyncIterable via hasattr check
                context.result = self._capture_response_id(
                    context.result,  # type: ignore[arg-type]
                    agui_thread_id,
                )
        elif agui_thread_id and context.result:
            # For non-streaming, extract and store the response_id
            new_response_id = self._extract_response_id(context)
            if new_response_id and new_response_id.startswith(("resp_", "conv_")):
                _thread_response_store[agui_thread_id] = new_response_id
                logger.debug("[ResponsesApiThreadMiddleware] Stored response_id %s for thread %s", new_response_id, agui_thread_id)
    
    async def _capture_response_id(
        self,
        stream: AsyncIterable[ChatResponseUpdate],
        agui_thread_id: str | None,
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Pass through stream unchanged, only capturing response_id at the end.
        
        Also detects if the response ends with a frontend-only tool call.
        """
        last_response_id: str | None = None
        last_tool_name: str | None = None
        
        async for update in stream:
            if update.response_id:
                last_response_id = update.response_id
            if update.conversation_id:
                last_response_id = update.conversation_id
            
            # Track tool calls to detect frontend-only tools
            if update.contents:
                for content in update.contents:
                    if _is_function_call(content):
                        # Track the tool name (will be overwritten for each tool call)
                        tool_name = content.name
                        if tool_name:
                            last_tool_name = tool_name
                            logger.debug("[ResponsesApiThreadMiddleware] Saw tool call: %s", tool_name)
            
            yield update
        
        # Check if the response ended with a frontend-only tool call
        # This happens when the LLM decides to call a frontend tool and stops
        ended_with_frontend = last_tool_name in FRONTEND_ONLY_TOOLS if last_tool_name else False
        
        if ended_with_frontend:
            # STORE the response_id - Azure is waiting for the tool result
            # When CopilotKit sends the result back, we'll continue the conversation
            logger.info("[ResponsesApiThreadMiddleware] Response ended with frontend tool '%s' - STORING response_id for continuation", last_tool_name)
            if agui_thread_id and last_response_id:
                if last_response_id.startswith(("resp_", "conv_")):
                    _thread_response_store[agui_thread_id] = last_response_id
                    logger.info("[ResponsesApiThreadMiddleware] Stored response_id %s for thread %s (awaiting tool result)", last_response_id, agui_thread_id)
        elif agui_thread_id and last_response_id:
            if last_response_id.startswith(("resp_", "conv_")):
                _thread_response_store[agui_thread_id] = last_response_id
                logger.info("[ResponsesApiThreadMiddleware] Stored response_id %s for thread %s", last_response_id, agui_thread_id)
    
    def _extract_response_id(self, context: ChatContext) -> str | None:
        """Extract the response_id from the result."""
        result = context.result
        if result is None:
            return None
        
        # For non-streaming (ChatResponse)
        if isinstance(result, ChatResponse):
            return result.response_id or result.conversation_id
        
        return None
    
    def _filter_messages_for_api(self, context: ChatContext) -> None:
        """Filter messages when continuing a conversation.
        
        When we have a stored response_id, the server already has the conversation
        history. We only need to send new messages to avoid KeyError on call_id_to_id.
        
        New messages can be:
        - A new user message (user asking a follow-up question)
        - A tool result message (frontend tool returning results)
        
        We find the last "new input" and send only that.
        For tool results, we send just the tool result message.
        For user messages, we send just that message.
        
        NOTE: This modifies context.messages (what gets sent to API) but NOT the
        orchestrator's input_data (which is used for MessagesSnapshotEvent).
        """
        messages = context.messages
        if not messages:
            return
        
        original_count = len(messages)
        
        # Check if the last message is a tool result - if so, send just that
        last_msg = messages[-1]
        last_role = getattr(last_msg, 'role', None)
        
        if last_role == Role.TOOL:
            # This is a tool result from CopilotKit - send only this message
            # Azure is waiting for this to continue the conversation
            context.messages.clear()
            context.messages.append(last_msg)
            logger.debug("[ResponsesApiThreadMiddleware] Continuation: sending tool result only: %d -> %d", original_count, len(context.messages))
            return
        
        # Find the last user message - that's what we need for a normal continuation
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            role = getattr(msg, 'role', None)
            if role == Role.USER:
                last_user_idx = i
                break
        
        if last_user_idx >= 0:
            # Only send the last user message - server has the rest
            last_user_msg = messages[last_user_idx]
            context.messages.clear()
            context.messages.append(last_user_msg)
            logger.debug("[ResponsesApiThreadMiddleware] Continuation: sending last user message only: %d -> %d", original_count, len(context.messages))
    
    def _filter_messages_for_fresh_start(self, context: ChatContext) -> None:
        """Filter messages for a fresh conversation start.
        
        When we're starting fresh (no stored response_id), we may still have
        message history from CopilotKit that includes tool calls from previous
        turns. These cause KeyError in call_id_to_id because the SDK doesn't
        know about them.
        
        This method removes:
        - Assistant messages with FunctionCallContent (tool call invocations)
        - Tool messages (FunctionResultContent)
        
        We keep user messages and pure text assistant messages.
        """
        messages = context.messages
        if not messages:
            return
        
        original_count = len(messages)
        filtered = []
        
        logger.debug("[ResponsesApiThreadMiddleware] _filter_messages_for_fresh_start: examining %d messages", original_count)
        
        for i, msg in enumerate(messages):
            role = getattr(msg, 'role', None)
            
            # Log message details - check both 'content' and 'contents' (different SDK versions use different names)
            contents_info = []
            msg_contents = getattr(msg, 'contents', None) or getattr(msg, 'content', None)
            if msg_contents:
                for c in (msg_contents if isinstance(msg_contents, list) else [msg_contents]):
                    c_type = type(c).__name__
                    call_id = getattr(c, 'call_id', None)
                    if call_id:
                        contents_info.append(f"{c_type}(call_id={call_id[:12]}...)")
                    else:
                        contents_info.append(c_type)
            logger.debug("[ResponsesApiThreadMiddleware]   msg[%d]: role=%s, contents=%s", i, role, contents_info)
            
            # Always keep user messages
            if role == Role.USER:
                logger.debug("[ResponsesApiThreadMiddleware]     -> KEEP (user)")
                filtered.append(msg)
                continue
            
            # Skip tool messages entirely
            if role == Role.TOOL:
                logger.debug("[ResponsesApiThreadMiddleware]     -> REMOVE (tool role)")
                continue
            
            # For assistant messages, check if they contain tool calls or tool results
            if role == Role.ASSISTANT:
                has_tool_related = False
                msg_contents = getattr(msg, 'contents', None) or getattr(msg, 'content', None)
                if msg_contents:
                    contents = msg_contents if isinstance(msg_contents, list) else [msg_contents]
                    for c in contents:
                        if _is_function_call(c) or _is_function_result(c):
                            has_tool_related = True
                            break
                        # Also check for any content with call_id attribute
                        if hasattr(c, 'call_id') and c.call_id:
                            has_tool_related = True
                            break
                
                if has_tool_related:
                    logger.debug("[ResponsesApiThreadMiddleware]     -> REMOVE (assistant with tool call/result)")
                    continue
                
                # Keep pure text assistant messages
                logger.debug("[ResponsesApiThreadMiddleware]     -> KEEP (pure text assistant)")
                filtered.append(msg)
                continue
            
            # Keep other message types (system, etc.)
            logger.debug("[ResponsesApiThreadMiddleware]     -> KEEP (other role)")
            filtered.append(msg)
        
        if len(filtered) != original_count:
            context.messages.clear()
            context.messages.extend(filtered)
            logger.debug("[ResponsesApiThreadMiddleware] Fresh start filter: %d -> %d messages", original_count, len(filtered))


async def deduplicate_tool_calls(
    stream: AsyncIterable[ChatResponseUpdate],
    agui_thread_id: str | None,
) -> AsyncIterable[ChatResponseUpdate]:
    """Wrap a streaming response to deduplicate tool call events.
    
    The v2 Responses API can emit the same tool call multiple times in a response,
    which causes AG-UI to throw "TOOL_CALL_START already in progress" errors.
    
    This wrapper tracks seen tool call IDs and filters out duplicates while
    preserving all other update properties (especially finish_reason which is
    required for AG-UI to properly close text messages).
    
    NOTE: This function is currently unused - the AG-UI framework's orchestrator
    handles deduplication at the event level instead.
    """
    seen_tool_call_ids: set[str] = set()
    last_response_id: str | None = None
    
    async for update in stream:
        # Track the response_id for thread mapping
        if update.response_id:
            last_response_id = update.response_id
        if update.conversation_id:
            last_response_id = update.conversation_id
        
        # Filter out duplicate tool calls from contents
        if update.contents:
            filtered_contents = []
            has_duplicates = False
            
            for content in update.contents:
                if _is_function_call(content):
                    call_id = content.call_id
                    if call_id and call_id in seen_tool_call_ids:
                        logger.debug("[Dedup] Filtering duplicate tool call: %s", call_id)
                        has_duplicates = True
                        continue
                    if call_id:
                        seen_tool_call_ids.add(call_id)
                filtered_contents.append(content)
            
            # Only modify the update if we actually filtered something
            if has_duplicates:
                # If no contents left but update has important metadata, still yield it
                # (finish_reason is critical for AG-UI to close text messages properly)
                if not filtered_contents and not update.finish_reason:
                    continue
                
                # Create new update with filtered contents
                update = ChatResponseUpdate(
                    role=update.role,
                    contents=filtered_contents if filtered_contents else None,
                    response_id=update.response_id,
                    conversation_id=update.conversation_id,
                    message_id=update.message_id,
                    model_id=update.model_id,
                    finish_reason=update.finish_reason,
                    raw_representation=update.raw_representation,
                    created_at=update.created_at,
                    author_name=update.author_name,
                    additional_properties=update.additional_properties,
                )
        
        yield update
    
    # After streaming completes, store the response_id for thread mapping
    if agui_thread_id and last_response_id:
        if last_response_id.startswith(("resp_", "conv_")):
            _thread_response_store[agui_thread_id] = last_response_id
            logger.debug("[Dedup] Stored response_id %s for thread %s", last_response_id, agui_thread_id)
