"""
Recommendations Agent - A2A Server

This is a simple A2A-protocol agent that provides logistics recommendations.
It uses the a2a-sdk to host a proper A2A JSON-RPC endpoint.
"""

from __future__ import annotations

import importlib
import logging
import os
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from a2a.helpers.proto_helpers import new_artifact, new_task, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Part,
    TaskState,
)
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

_trace_module: Any = None
try:  # pragma: no cover
    _trace_module = importlib.import_module("opentelemetry.trace")
except ImportError:
    _trace_module = None

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

# Suppress noisy Azure exporter/network diagnostics while keeping warnings/errors.
for noisy_logger in (
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.monitor.opentelemetry.exporter",
    "azure.monitor.opentelemetry.exporter._quickpulse._manager",
    "azure.monitor.opentelemetry.exporter.export._base",
):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

ATTR_CONVERSATION_ID = "gen_ai.conversation.id"
ATTR_TURN_ID = "gen_ai.turn.id"
ATTR_RUN_ID = "gen_ai.run.id"
ATTR_A2A_INTERACTION_ID = "gen_ai.a2a.interaction.id"

NOISY_A2A_SPAN_PREFIXES = (
    "a2a.server.events.event_queue_v2.",
    "a2a.server.request_handlers.default_request_handler_v2.",
    "a2a.server.routes.jsonrpc_dispatcher.",
)


def _should_suppress_internal_a2a_spans() -> bool:
    return os.getenv("A2A_SUPPRESS_INTERNAL_SPANS", "true").lower() == "true"


def _wrap_span_processors_with_filters() -> None:
    """Wrap provider span processors to suppress verbose internal A2A spans."""
    if not _should_suppress_internal_a2a_spans():
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import SpanProcessor

        class _FilteringSpanProcessor(SpanProcessor):
            def __init__(self, delegate: SpanProcessor):
                self._delegate = delegate

            def on_start(self, span: Any, parent_context: Any | None = None) -> None:
                self._delegate.on_start(span, parent_context)

            def on_end(self, span: Any) -> None:
                if any(span.name.startswith(prefix) for prefix in NOISY_A2A_SPAN_PREFIXES):
                    return
                self._delegate.on_end(span)

            def shutdown(self) -> None:
                self._delegate.shutdown()

            def force_flush(self, timeout_millis: int = 30_000) -> bool:
                return self._delegate.force_flush(timeout_millis)

        provider = trace.get_tracer_provider()
        active_processor = getattr(provider, "_active_span_processor", None)
        if active_processor is None:
            return
        current_processors = getattr(active_processor, "_span_processors", None)
        if not isinstance(current_processors, tuple):
            return

        if any(isinstance(processor, _FilteringSpanProcessor) for processor in current_processors):
            return

        wrapped_processors = tuple(_FilteringSpanProcessor(p) for p in current_processors)
        active_processor._span_processors = wrapped_processors
        logger.info("Suppressed internal A2A SDK spans with prefixes: %s", NOISY_A2A_SPAN_PREFIXES)
    except Exception as exc:
        logger.warning("Failed to apply A2A internal span suppression: %s", exc)


def _is_observability_enabled() -> bool:
    return os.getenv("ENABLE_INSTRUMENTATION", "false").lower() == "true"


def configure_observability() -> None:
    """Configure tracing exporters for App Insights or OTLP when enabled."""
    if not _is_observability_enabled():
        logger.info("Observability disabled (ENABLE_INSTRUMENTATION != true)")
        return

    telemetry_mode = os.getenv("TELEMETRY_MODE", "appinsights").lower()
    appinsights_connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")

    if telemetry_mode == "appinsights" and appinsights_connection:
        try:
            from azure.monitor.opentelemetry import (  # type: ignore[import-not-found]
                configure_azure_monitor,
            )
            from opentelemetry.sdk.resources import Resource

            configure_azure_monitor(
                connection_string=appinsights_connection,
                resource=Resource.create({"service.name": "a2a-agent"}),
                enable_live_metrics=False,
                instrumentation_options={
                    "fastapi": {"enabled": True},
                    "requests": {"enabled": True},
                    "urllib3": {"enabled": True},
                },
            )
            _wrap_span_processors_with_filters()
            logger.info("OpenTelemetry configured with Azure Monitor")
            return
        except ImportError as exc:
            logger.warning(
                "Azure Monitor OpenTelemetry package not available; falling back to OTLP. %s", exc
            )
        except (RuntimeError, ValueError, OSError) as exc:
            logger.error("Failed to configure Azure Monitor exporter: %s", exc)

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not otlp_endpoint:
            logger.warning(
                "Observability enabled, but no exporter is configured. Set APPLICATIONINSIGHTS_CONNECTION_STRING "
                "or OTEL_EXPORTER_OTLP_ENDPOINT."
            )
            return

        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
        trace.set_tracer_provider(tracer_provider)
        _wrap_span_processors_with_filters()
        logger.info("OpenTelemetry configured with OTLP endpoint: %s", otlp_endpoint)
    except ImportError as exc:
        logger.warning("OTLP exporter packages not available: %s", exc)
    except (RuntimeError, ValueError, OSError) as exc:
        logger.error("Failed to configure OTLP exporters: %s", exc)


class _NoOpSpan:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def set_attribute(self, _key: str, _value: object) -> None:
        return

    def record_exception(self, _exc: Exception) -> None:
        return

    def end(self) -> None:
        return


class _NoOpTracer:
    def start_as_current_span(self, _name: str, context: Any = None) -> _NoOpSpan:
        return _NoOpSpan()

    def start_span(self, _name: str, context: Any = None) -> _NoOpSpan:
        return _NoOpSpan()


tracer = _trace_module.get_tracer("recommendations.a2a") if _trace_module else _NoOpTracer()

# Sample recommendations pool
RECOMMENDATIONS_POOL = [
    "Consider consolidating shipments on the LAX-ORD route to improve capacity utilization by 15-20%.",
    "Implement predictive maintenance scheduling for high-traffic routes to reduce unexpected delays.",
    "Use historical data analysis to optimize flight schedules during peak shipping seasons.",
    "Consider adding a mid-week flight on underutilized routes to balance weekly capacity.",
    "Implement dynamic pricing based on real-time capacity utilization to maximize revenue.",
    "Review fuel efficiency metrics for routes with consistently high utilization.",
    "Consider partnering with ground carriers for last-mile delivery optimization.",
    "Implement automated alerts for flights approaching capacity thresholds.",
    "Use machine learning models to predict demand spikes 48-72 hours in advance.",
    "Consider weather-based route alternatives for critical shipments during storm seasons.",
    "Optimize container loading patterns to maximize cubic feet utilization.",
    "Implement cross-docking strategies at hub airports to reduce handling time.",
    "Consider time-definite service tiers to better match capacity with customer needs.",
    "Review and update risk assessment criteria based on recent operational data.",
    "Implement real-time tracking dashboards for high-priority shipments.",
]


def generate_recommendations(count: int = 3) -> str:
    """Generate random recommendations from the pool."""
    num_recommendations = min(max(count, 2), 5)  # Ensure 2-5 range
    selected = random.sample(RECOMMENDATIONS_POOL, num_recommendations)
    formatted = "\n".join([f"{i + 1}. {rec}" for i, rec in enumerate(selected)])
    return f"Here are {num_recommendations} recommendations:\n\n{formatted}"


def _set_remote_correlation_attributes(span: Any, context: RequestContext) -> None:
    """Apply propagated caller correlation IDs to remote spans when present."""
    metadata = context.metadata if context.metadata else {}

    if metadata.get(ATTR_A2A_INTERACTION_ID):
        span.set_attribute(ATTR_A2A_INTERACTION_ID, metadata[ATTR_A2A_INTERACTION_ID])
    if metadata.get(ATTR_CONVERSATION_ID):
        span.set_attribute(ATTR_CONVERSATION_ID, metadata[ATTR_CONVERSATION_ID])
    elif context.message and context.message.context_id:
        span.set_attribute(ATTR_CONVERSATION_ID, context.message.context_id)

    if metadata.get(ATTR_TURN_ID):
        span.set_attribute(ATTR_TURN_ID, metadata[ATTR_TURN_ID])
    if metadata.get(ATTR_RUN_ID):
        span.set_attribute(ATTR_RUN_ID, metadata[ATTR_RUN_ID])


class RecommendationsAgentExecutor(AgentExecutor):
    """Simple agent executor that generates recommendations."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent and generate recommendations."""
        with tracer.start_as_current_span("a2a.recommendations.execute") as span:
            _set_remote_correlation_attributes(span, context)
            span.set_attribute("gen_ai.a2a.source_agent", "logistics-agent")
            span.set_attribute("gen_ai.a2a.target_agent", "recommendations-agent")
            span.set_attribute("gen_ai.a2a.operation", "recommendations")
            span.set_attribute("gen_ai.a2a.status", "started")
            logger.info("Executing recommendations agent")

            # Extract the user message from the request
            user_message = ""
            if context.message and context.message.parts:
                for part in context.message.parts:
                    text = getattr(part, "text", "")
                    if text:
                        user_message = text
                        break

            logger.info(f"Received message: {user_message}")
            span.set_attribute("a2a.message.length", len(user_message))

            try:
                if "simulate-timeout" in user_message.lower():
                    raise TimeoutError("Simulated timeout for validation")

                # Generate recommendations
                recommendations = generate_recommendations(3)

                # Create response message
                response_parts: list[Part] = [new_text_part(recommendations)]

                # Create artifact with the response
                artifact = new_artifact(
                    parts=response_parts,
                    name="recommendations",
                    description="Logistics recommendations",
                )

                # Create completed task
                task = new_task(
                    task_id=context.task_id or "task-1",
                    context_id=context.context_id or "context-1",
                    state=TaskState.TASK_STATE_COMPLETED,
                    artifacts=[artifact],
                )

                # Send the completed task event
                await event_queue.enqueue_event(task)
                span.set_attribute("gen_ai.a2a.status", "completed")
                logger.info("Recommendations generated and sent")
            except TimeoutError as exc:
                span.set_attribute("gen_ai.a2a.status", "timeout")
                span.record_exception(exc)
                failed = new_task(
                    task_id=context.task_id or "task-1",
                    context_id=context.context_id or "context-1",
                    state=TaskState.TASK_STATE_FAILED,
                    artifacts=[],
                )
                await event_queue.enqueue_event(failed)
                logger.error("Recommendations timeout: %s", exc)
                return
            except Exception as exc:
                span.set_attribute("gen_ai.a2a.status", "failed")
                span.record_exception(exc)
                failed = new_task(
                    task_id=context.task_id or "task-1",
                    context_id=context.context_id or "context-1",
                    state=TaskState.TASK_STATE_FAILED,
                    artifacts=[],
                )
                await event_queue.enqueue_event(failed)
                logger.error("Recommendations execution failed: %s", exc)
                raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle cancellation."""
        logger.info("Cancellation requested")


def create_agent_card() -> AgentCard:
    """Create the A2A agent card for discovery."""
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False,
    )

    recommendations_skill = AgentSkill(
        id="recommendations",
        name="Recommendations",
        description="Provides logistics recommendations for capacity optimization and risk mitigation.",
        tags=["logistics", "recommendations", "optimization"],
        examples=[
            "Give me 3 recommendations for optimizing capacity",
            "What should I do about over-utilized flights?",
            "Provide suggestions for risk mitigation",
        ],
    )

    return AgentCard(
        name="RecommendationsAgent",
        description="An A2A agent that provides logistics recommendations for capacity optimization and risk mitigation.",
        version="1.0.0",
        documentation_url="",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=capabilities,
        skills=[recommendations_skill],
    )


def _register_a2a_routes(app: FastAPI) -> None:
    """Register A2A card, JSON-RPC, and REST routes on the FastAPI app."""
    agent_card = create_agent_card()

    # Create the agent executor
    agent_executor = RecommendationsAgentExecutor()

    # Create task store for managing tasks
    task_store = InMemoryTaskStore()

    # Create the request handler
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(agent_card),
        jsonrpc_routes=create_jsonrpc_routes(
            request_handler,
            rpc_url="/",
            enable_v0_3_compat=True,
        ),
        rest_routes=create_rest_routes(
            request_handler,
            enable_v0_3_compat=True,
        ),
    )


# Create FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for the FastAPI app."""
    configure_observability()
    logger.info("Recommendations A2A Agent starting...")
    yield
    logger.info("Recommendations A2A Agent shutting down...")


app = FastAPI(
    title="Recommendations A2A Agent",
    description="A2A-protocol agent that provides logistics recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "recommendations-agent", "protocol": "A2A"}


# Register A2A routes at root (after health endpoint is defined)
_register_a2a_routes(app)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5002"))
    logger.info(f"Starting Recommendations A2A Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
