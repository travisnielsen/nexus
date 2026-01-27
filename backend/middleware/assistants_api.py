"""
Assistants API Thread Middleware

This module provides middleware for managing Azure Foundry Assistants API conversation continuity.
It maps AG-UI client thread IDs to Azure Assistant thread IDs.

The Assistants API has native thread support, making this middleware simpler than
the Responses API middleware. Key differences:
- Threads are first-class objects (no response_id chaining)
- Server maintains conversation state in threads automatically
- Simpler message handling - server manages history via thread_id

IMPORTANT: CopilotKit v1.x Thread Behavior
------------------------------------------
CopilotKit v1.x React generates a NEW AG-UI thread_id for each "run" (each user message
that triggers LLM inference), not a persistent session-level ID. This is by design in 
the current AG-UI protocol implementation.

As a result, each user message within a browser session may arrive with a different 
AG-UI thread_id, causing this middleware to create new Azure Foundry threads for each
message. This is expected behavior and does not affect functionality because:

1. AG-UI sends full message history with each request
2. The LLM maintains conversational context through the message payload
3. Azure threads are lightweight and the cost impact is minimal

CopilotKit v2.x (@copilotkitnext packages) improves this with:
- Thread ID generated once per component instance (not per run)
- SqliteAgentRunner for persistent thread storage
- connect() method to reconnect to existing threads after page refresh

When upgrading to CopilotKit v2.x stable, this middleware's thread mapping will work
correctly (same AG-UI thread_id → same Azure thread_id for entire session).

See: https://github.com/CopilotKit/CopilotKit/tree/main/src/v2.x/packages/runtime/src/runner
"""

from __future__ import annotations

from typing import Callable, Awaitable
from collections.abc import AsyncIterable
import logging

from agent_framework._types import ChatResponse, ChatResponseUpdate, Content, Role
from agent_framework._middleware import ChatMiddleware, ChatContext

# Import the shared ContextVar from responses_api - the orchestrator sets this
# and we need to read the same one (not a separate ContextVar)
from .responses_api import get_current_agui_thread_id as _get_shared_agui_thread_id


logger = logging.getLogger(__name__)


def _is_function_call(content: Content) -> bool:
    """Check if content is a function call."""
    return getattr(content, 'type', None) == 'function_call'


# Thread mapping store: maps AG-UI thread_id (client UUID) to Azure Assistant thread_id
# This allows us to continue conversations across multiple requests
_agui_to_assistant_thread_store: dict[str, str] = {}


# Frontend-only tools that are handled by CopilotKit, not the backend
# These tools don't send results back to Azure, so we need special handling
FRONTEND_ONLY_TOOLS = {
    "filter_dashboard",
    "setThemeColor",
    "display_flight_list",
    "display_flight_detail",
    "display_historical_chart",
}


def get_assistant_thread_store() -> dict[str, str]:
    """Get the AG-UI thread_id to Assistant thread_id mapping store."""
    return _agui_to_assistant_thread_store


class AssistantsApiThreadMiddleware(ChatMiddleware):
    """Chat middleware that manages thread ID mapping for Assistants API.
    
    The Assistants API uses native thread objects for conversation continuity.
    AG-UI sends a client-generated thread_id (UUID), but we need to map this
    to an Azure Assistant thread_id.
    
    This middleware is simpler than ResponsesApiThreadMiddleware because:
    1. Threads are first-class objects in Assistants API
    2. Server maintains conversation history automatically
    3. No need to filter messages for fresh starts - server handles it
    
    This middleware:
    1. Before request: Gets AG-UI thread_id and sets Azure thread_id if we have one stored
    2. After response: Stores the Azure thread_id for the next request
    """
    
    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],  # noqa: A002 - required by base class
    ) -> None:
        """Process the chat request, managing thread ID mapping."""
        # Get the AG-UI thread_id from the SHARED ContextVar (set by AG-UI framework's orchestrator)
        # This is the same ContextVar used by responses_api - the orchestrator sets it
        shared_context_var = _get_shared_agui_thread_id()
        agui_thread_id = shared_context_var.get()
        
        # Log clearly for diagnosing thread fragmentation
        short_agui = agui_thread_id[:12] + "..." if agui_thread_id and len(agui_thread_id) > 12 else agui_thread_id
        stored_ids = list(_agui_to_assistant_thread_store.keys())
        logger.debug("="*60)
        logger.debug("[AssistantsApiThreadMiddleware] INCOMING AG-UI thread_id: %s", short_agui)
        logger.debug("[AssistantsApiThreadMiddleware] TOTAL threads in store: %d", len(stored_ids))
        if stored_ids:
            logger.debug("[AssistantsApiThreadMiddleware] Known AG-UI thread_ids: %s", 
                       [tid[:12] + "..." for tid in stored_ids])
        logger.debug("[AssistantsApiThreadMiddleware] Incoming messages: %d", len(context.messages) if context.messages else 0)
        
        # Check if we have a stored Azure thread_id for this AG-UI thread
        if agui_thread_id and agui_thread_id in _agui_to_assistant_thread_store:
            stored_thread_id = _agui_to_assistant_thread_store[agui_thread_id]
            logger.debug("[AssistantsApiThreadMiddleware] CONTINUING with Azure thread_id: %s", stored_thread_id)
            
            # Set conversation_id in context options for the client
            # NOTE: AzureAIAgentClient uses 'conversation_id' in options (not 'thread_id')
            # It internally maps: options.get("conversation_id") -> run_options["thread_id"]
            if context.options is None:
                context.options = {}
            context.options["conversation_id"] = stored_thread_id
            
            # For Assistants API, we only need to send the new message(s)
            # The server has the full history via the thread
            self._filter_to_new_messages(context)
        else:
            logger.debug("[AssistantsApiThreadMiddleware] NEW conversation - no stored thread_id for AG-UI thread: %s", agui_thread_id)
            # New conversation - the client will create a new thread
            # Filter out any old tool calls that might cause issues
            self._filter_messages_for_fresh_start(context)
        
        logger.debug("[AssistantsApiThreadMiddleware] After filtering: %d messages", 
                    len(context.messages) if context.messages else 0)
        
        # Call the next middleware/handler
        await next(context)
        
        # Capture thread_id from the response
        if context.is_streaming and context.result is not None:
            if hasattr(context.result, '__aiter__'):
                context.result = self._capture_thread_id(
                    context.result,  # type: ignore[arg-type]
                    agui_thread_id,
                )
        elif agui_thread_id and context.result:
            # For non-streaming, extract and store the thread_id
            thread_id = self._extract_thread_id(context)
            if thread_id:
                _agui_to_assistant_thread_store[agui_thread_id] = thread_id
                logger.debug("[AssistantsApiThreadMiddleware] Stored thread_id %s for AG-UI thread %s", 
                           thread_id, agui_thread_id)
    
    async def _capture_thread_id(
        self,
        stream: AsyncIterable[ChatResponseUpdate],
        agui_thread_id: str | None,
    ) -> AsyncIterable[ChatResponseUpdate]:
        """Pass through stream, capturing thread_id for storage."""
        captured_thread_id: str | None = None
        last_tool_name: str | None = None
        update_count = 0
        
        async for update in stream:
            update_count += 1
            
            # Capture thread_id from updates - only log on first capture
            # Try multiple sources in order of preference
            new_thread_id: str | None = None
            
            # 1. Direct thread_id attribute
            if hasattr(update, 'thread_id') and update.thread_id:
                new_thread_id = update.thread_id
            
            # 2. conversation_id that looks like a thread ID
            elif update.conversation_id and update.conversation_id.startswith("thread_"):
                new_thread_id = update.conversation_id
            
            # 3. Check response_id as well (might contain thread reference)
            elif update.response_id and update.response_id.startswith("thread_"):
                new_thread_id = update.response_id
            
            # 4. Check raw_representation for thread info
            elif hasattr(update, 'raw_representation') and update.raw_representation:
                raw = update.raw_representation
                if isinstance(raw, dict):
                    if 'thread_id' in raw:
                        new_thread_id = raw['thread_id']
                    elif 'thread' in raw and isinstance(raw['thread'], dict) and 'id' in raw['thread']:
                        new_thread_id = raw['thread']['id']
            
            # Only log once when first captured or if it changes (unusual)
            if new_thread_id:
                if captured_thread_id is None:
                    captured_thread_id = new_thread_id
                    logger.debug("[AssistantsApiThreadMiddleware] Captured thread_id: %s", captured_thread_id)
                elif captured_thread_id != new_thread_id:
                    captured_thread_id = new_thread_id
                    logger.warning("[AssistantsApiThreadMiddleware] thread_id changed mid-stream: %s", captured_thread_id)
            
            # Track tool calls for frontend tool detection
            if update.contents:
                for content in update.contents:
                    if _is_function_call(content):
                        tool_name = content.name
                        if tool_name:
                            last_tool_name = tool_name
                            logger.debug("[AssistantsApiThreadMiddleware] Saw tool call: %s", tool_name)
            
            yield update
        
        logger.debug("[AssistantsApiThreadMiddleware] Stream complete. Total updates: %d", update_count)
        
        # Check if response ended with frontend-only tool
        ended_with_frontend = last_tool_name in FRONTEND_ONLY_TOOLS if last_tool_name else False
        
        if ended_with_frontend:
            logger.debug("[AssistantsApiThreadMiddleware] Response ended with frontend tool '%s'", last_tool_name)
            # For Assistants API, we still store the thread_id because the thread maintains state
            # The frontend will send the tool result back and we'll continue
        
        # Store the thread_id mapping
        if agui_thread_id and captured_thread_id:
            _agui_to_assistant_thread_store[agui_thread_id] = captured_thread_id
            logger.debug("[AssistantsApiThreadMiddleware] STORED thread_id %s for AG-UI thread %s", 
                       captured_thread_id, agui_thread_id)
        elif agui_thread_id:
            logger.warning("[AssistantsApiThreadMiddleware] NO thread_id captured for AG-UI thread %s!", agui_thread_id)
    
    def _extract_thread_id(self, context: ChatContext) -> str | None:
        """Extract the thread_id from the result."""
        result = context.result
        if result is None:
            return None
        
        if isinstance(result, ChatResponse):
            # Check for thread_id attribute
            if hasattr(result, 'thread_id') and result.thread_id:
                return result.thread_id
            # Fallback to conversation_id if it looks like a thread ID
            if result.conversation_id and result.conversation_id.startswith("thread_"):
                return result.conversation_id
        
        return None
    
    def _filter_to_new_messages(self, context: ChatContext) -> None:
        """Filter to only new messages when continuing a conversation.
        
        With Assistants API, the server maintains thread history automatically.
        We only need to send new messages (typically the last user message
        or a tool result).
        """
        messages = context.messages
        if not messages:
            return
        
        original_count = len(messages)
        
        # Check if last message is a tool result - send just that
        last_msg = messages[-1]
        last_role = getattr(last_msg, 'role', None)
        
        if last_role == Role.TOOL:
            context.messages.clear()
            context.messages.append(last_msg)
            logger.debug("[AssistantsApiThreadMiddleware] Continuation: sending tool result only: %d -> %d", 
                        original_count, len(context.messages))
            return
        
        # Find the last user message
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            role = getattr(msg, 'role', None)
            if role == Role.USER:
                last_user_msg = messages[i]
                context.messages.clear()
                context.messages.append(last_user_msg)
                logger.debug("[AssistantsApiThreadMiddleware] Continuation: sending last user message only: %d -> %d", 
                            original_count, len(context.messages))
                return
        
        # Fallback: send all messages (shouldn't happen in normal flow)
        logger.debug("[AssistantsApiThreadMiddleware] Continuation: keeping all messages (no user message found)")
    
    def _filter_messages_for_fresh_start(self, context: ChatContext) -> None:
        """Filter messages for a fresh conversation start.
        
        For fresh starts, we only send the LAST user message.
        The full conversation history will confuse the LLM into repeating
        previous actions instead of responding to the new message.
        
        This is different from _filter_to_new_messages which is for continuations.
        For fresh starts (new thread), we want minimal context.
        """
        messages = context.messages
        if not messages:
            return
        
        original_count = len(messages)
        
        # Find the last user message - that's the only one we need
        last_user_msg = None
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            role = getattr(msg, 'role', None)
            if role == Role.USER:
                last_user_msg = msg
                break
        
        if last_user_msg:
            context.messages.clear()
            context.messages.append(last_user_msg)
            logger.debug("[AssistantsApiThreadMiddleware] Fresh start filter: sending last user message only: %d -> 1", 
                        original_count)
        else:
            # No user message found - keep empty
            context.messages.clear()
            logger.debug("[AssistantsApiThreadMiddleware] Fresh start filter: no user message found, cleared: %d -> 0", 
                        original_count)


def clear_thread_mapping(agui_thread_id: str) -> bool:
    """Clear the stored thread mapping for an AG-UI thread.
    
    This is useful when we need to reset conversation state,
    such as after a frontend-only tool that ends the conversation.
    
    Args:
        agui_thread_id: The AG-UI thread ID to clear
        
    Returns:
        True if a mapping was cleared, False if none existed
    """
    if agui_thread_id in _agui_to_assistant_thread_store:
        del _agui_to_assistant_thread_store[agui_thread_id]
        logger.debug("[AssistantsApiThreadMiddleware] Cleared thread mapping for %s", agui_thread_id)
        return True
    return False
