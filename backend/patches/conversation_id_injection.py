"""
Patch: Conversation ID Injection for Azure Foundry Tracing

The Azure SDK instrumentor has issues preventing conversation_id from appearing in traces:

1. The _extract_conversation_id method looks for `conversation` or `conversation_id` in kwargs,
   but the agent-framework passes `previous_response_id` instead.

2. Even if _extract_conversation_id returns a value, the _create_event_attributes method
   has the conversation_id setting commented out in the SDK.

This patch fixes both issues by:
1. Wrapping _extract_conversation_id to inject our thread_id from ContextVar
2. Wrapping _create_event_attributes to set the GEN_AI_CONVERSATION_ID attribute

Additionally, this patch instruments the agent-framework's tool execution spans to include
the conversation_id, enabling full session correlation.

The thread_id is obtained from the _current_agui_thread_id ContextVar, which is
set by the AG-UI event stream patch from CopilotKit's useCopilotReadable context.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Track if patches were applied to prevent double-patching
_patch_applied = False
_tool_patch_applied = False
_original_extract_conversation_id = None
_original_create_event_attributes = None
_original_start_responses_span = None
_original_get_function_span = None


def apply_conversation_id_injection_patch() -> bool:
    """Patch Azure SDK to inject our thread_id as conversation_id for tracing.
    
    Returns:
        True if patch was applied, False otherwise.
    """
    global _patch_applied, _original_extract_conversation_id, _original_create_event_attributes, _original_start_responses_span
    
    if _patch_applied:
        logger.debug("[CONV-ID-PATCH] Already applied, skipping")
        return True
    
    try:
        from middleware.responses_api import get_current_agui_thread_id
        
        try:
            from azure.ai.projects.telemetry._responses_instrumentor import (
                _ResponsesInstrumentorPreview,
                GEN_AI_CONVERSATION_ID,
            )
            from azure.ai.projects.telemetry._utils import GEN_AI_THREAD_ID
        except ImportError:
            logger.debug("[CONV-ID-PATCH] Azure SDK telemetry not available, skipping patch")
            return False
        
        # Save original methods
        _original_extract_conversation_id = _ResponsesInstrumentorPreview._extract_conversation_id  # type: ignore[attr-defined]
        _original_create_event_attributes = _ResponsesInstrumentorPreview._create_event_attributes  # type: ignore[attr-defined]
        _original_start_responses_span = _ResponsesInstrumentorPreview.start_responses_span  # type: ignore[attr-defined]
        
        def patched_extract_conversation_id(self, kwargs: Dict[str, Any]) -> Optional[str]:
            """Inject thread_id as conversation_id if original extraction returns None."""
            original_result = _original_extract_conversation_id(self, kwargs)  # type: ignore[misc]
            if original_result:
                return original_result
            
            thread_id = get_current_agui_thread_id().get()
            if thread_id:
                logger.debug("[CONV-ID-PATCH] Injected thread_id=%s as conversation_id", thread_id)
                return thread_id
            return None
        
        def patched_create_event_attributes(
            self,
            conversation_id: Optional[str] = None,
            message_role: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Set conversation_id attribute (re-enabling what SDK commented out)."""
            attrs = _original_create_event_attributes(self, conversation_id, message_role)  # type: ignore[misc]
            if conversation_id:
                attrs[GEN_AI_CONVERSATION_ID] = conversation_id
                attrs[GEN_AI_THREAD_ID] = conversation_id
            return attrs
        
        def patched_start_responses_span(
            self,
            server_address=None,
            port=None,
            model=None,
            assistant_name=None,
            conversation_id=None,
            input_text=None,
            input_raw=None,
            stream=False,
            tools=None,
        ):
            """Ensure conversation_id is explicitly set on the span."""
            span = _original_start_responses_span(
                self,
                server_address=server_address,
                port=port,
                model=model,
                assistant_name=assistant_name,
                conversation_id=conversation_id,
                input_text=input_text,
                input_raw=input_raw,
                stream=stream,
                tools=tools,
            )
            
            # Explicitly set attributes on the real span as backup
            if span and conversation_id:
                try:
                    real_span = getattr(span, 'span_instance', None)
                    if real_span and getattr(real_span, 'is_recording', lambda: False)():
                        real_span.set_attribute(GEN_AI_CONVERSATION_ID, conversation_id)
                        real_span.set_attribute(GEN_AI_THREAD_ID, conversation_id)
                except Exception:
                    pass  # Silently ignore - span attributes may already be set
            
            return span
        
        # Apply the patches
        _ResponsesInstrumentorPreview._extract_conversation_id = patched_extract_conversation_id  # type: ignore[attr-defined]
        _ResponsesInstrumentorPreview._create_event_attributes = patched_create_event_attributes  # type: ignore[attr-defined]
        _ResponsesInstrumentorPreview.start_responses_span = patched_start_responses_span  # type: ignore[attr-defined]
        
        _patch_applied = True
        logger.info("[CONV-ID-PATCH] Patched Azure SDK for conversation_id injection")
        return True
        
    except ImportError as e:
        logger.debug("[CONV-ID-PATCH] Could not import required modules: %s", e)
        return False
    except Exception as e:
        logger.warning("[CONV-ID-PATCH] Failed to apply patch: %s", e)
        return False


def apply_tool_execution_span_patch() -> bool:
    """Patch agent-framework to include conversation_id in tool execution spans.
    
    Returns:
        True if patch was applied, False otherwise.
    """
    global _tool_patch_applied, _original_get_function_span
    
    if _tool_patch_applied:
        logger.debug("[TOOL-SPAN-PATCH] Already applied, skipping")
        return True
    
    try:
        from middleware.responses_api import get_current_agui_thread_id
        from agent_framework import observability as af_observability
        
        try:
            from azure.ai.projects.telemetry._responses_instrumentor import GEN_AI_CONVERSATION_ID
            from azure.ai.projects.telemetry._utils import GEN_AI_THREAD_ID
        except ImportError:
            GEN_AI_CONVERSATION_ID = "gen_ai.conversation.id"
            GEN_AI_THREAD_ID = "gen_ai.thread.id"
        
        _original_get_function_span = af_observability.get_function_span
        
        def patched_get_function_span(attributes: dict[str, str]):
            """Add conversation_id to tool execution span attributes."""
            thread_id = get_current_agui_thread_id().get()
            if thread_id:
                attributes[GEN_AI_CONVERSATION_ID] = thread_id
                attributes[GEN_AI_THREAD_ID] = thread_id
            return _original_get_function_span(attributes)
        
        # Apply the patch
        af_observability.get_function_span = patched_get_function_span
        
        # Also patch the module-level import in _tools.py if already imported
        try:
            from agent_framework import _tools as af_tools
            af_tools.get_function_span = patched_get_function_span
        except (ImportError, AttributeError):
            pass
        
        _tool_patch_applied = True
        logger.info("[TOOL-SPAN-PATCH] Patched agent-framework for tool span conversation_id")
        return True
        
    except ImportError as e:
        logger.debug("[TOOL-SPAN-PATCH] Could not import required modules: %s", e)
        return False
    except Exception as e:
        logger.warning("[TOOL-SPAN-PATCH] Failed to apply patch: %s", e)
        return False
