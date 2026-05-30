"""
OpenTelemetry observability configuration for the Agent API.

This module provides telemetry configuration for monitoring agent performance,
tracing requests, and collecting metrics.

Environment variables:
- ENABLE_INSTRUMENTATION: Set to "true" to enable OpenTelemetry (default: false)
- TELEMETRY_MODE: "appinsights" (default) or "otlp" - selects the telemetry backend
- APPLICATIONINSIGHTS_CONNECTION_STRING: Azure Monitor connection string (for appinsights mode)
- OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint for Aspire Dashboard, Jaeger, etc. (for otlp mode)
- ENABLE_CONSOLE_EXPORTERS: Set to "true" to enable console output (default: false)
- ENABLE_SENSITIVE_DATA: Set to "true" to log prompts/responses (default: false)
"""

import logging
import os
from importlib import metadata

logger = logging.getLogger(__name__)


def _is_genai_tracing_supported() -> tuple[bool, str]:
    """Return whether the experimental GenAI tracing path is safe to enable.

    The current stack can break AG-UI streaming when this experimental path wraps
    response streams that the agent framework expects to expose `.parse()`.
    """
    force_enable = os.getenv("FORCE_ENABLE_EXPERIMENTAL_GENAI_TRACING", "false").lower()
    if force_enable == "true":
        return True, "forced by FORCE_ENABLE_EXPERIMENTAL_GENAI_TRACING=true"

    package_names = [
        "agent-framework-openai",
        "agent-framework-foundry",
        "azure-ai-projects",
        "openai",
    ]
    resolved_versions: dict[str, str] = {}
    for package_name in package_names:
        try:
            resolved_versions[package_name] = metadata.version(package_name)
        except metadata.PackageNotFoundError:
            resolved_versions[package_name] = "not-installed"

    version_summary = ", ".join(f"{name}={version}" for name, version in resolved_versions.items())

    return (
        False,
        f"blocked by default pending a verified-compatible SDK matrix ({version_summary})",
    )


def is_observability_enabled() -> bool:
    """Check if OpenTelemetry observability is enabled."""
    return os.getenv("ENABLE_INSTRUMENTATION", "false").lower() == "true"


def configure_observability() -> None:
    """
    Configure OpenTelemetry observability if enabled.

    Supports two backends based on TELEMETRY_MODE:
    - "appinsights" (default): Azure Monitor via APPLICATIONINSIGHTS_CONNECTION_STRING
    - "otlp": OTLP exporters via OTEL_EXPORTER_OTLP_ENDPOINT (for Aspire, Jaeger, Tempo)
    """
    if not is_observability_enabled():
        logger.info("Observability disabled (ENABLE_INSTRUMENTATION != true)")
        return

    if os.getenv("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING", "").lower() == "true":
        supported, reason = _is_genai_tracing_supported()
        if supported:
            logger.info("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true (%s)", reason)
        else:
            os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "false"
            logger.warning(
                "AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING was requested but disabled: %s",
                reason,
            )

    try:
        telemetry_mode = os.getenv("TELEMETRY_MODE", "appinsights").lower()
        azure_monitor_connection = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

        if telemetry_mode == "otlp":
            _configure_otlp_exporters()
        elif azure_monitor_connection:
            _configure_azure_monitor(azure_monitor_connection)
        else:
            logger.warning(
                "TELEMETRY_MODE=appinsights but APPLICATIONINSIGHTS_CONNECTION_STRING not set"
            )
            _configure_otlp_exporters()

    except ImportError as e:
        logger.warning("OpenTelemetry packages not available: %s", e)
    except (RuntimeError, ValueError, OSError) as e:
        logger.error("Failed to configure OpenTelemetry: %s", e)


def _configure_azure_monitor(connection_string: str) -> None:
    """Configure Azure Monitor for production telemetry.

    Note: configure_azure_monitor() sets up a TracerProvider with an Azure Monitor exporter.
    The Agent Framework's enable_instrumentation() then uses this global TracerProvider
    for all its spans. We previously added a second exporter which caused duplicate spans.
    """
    try:
        from agent_framework.observability import create_resource, enable_instrumentation
        from azure.monitor.opentelemetry import (  # type: ignore[import-not-found]
            configure_azure_monitor,
        )

        enable_sensitive = os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() == "true"

        # Create resource for Azure Monitor
        resource = create_resource()

        # Configure Azure Monitor with instrumentation options
        # This sets up the global TracerProvider with an Azure Monitor exporter
        # Enable azure_sdk to trace Azure AI Foundry/Inference calls
        configure_azure_monitor(
            connection_string=connection_string,
            resource=resource,
            enable_live_metrics=True,
            instrumentation_options={
                "azure_sdk": {"enabled": True},  # Trace Azure SDK calls (AI Foundry)
                "fastapi": {"enabled": True},  # Trace FastAPI requests
                "requests": {"enabled": True},  # Trace HTTP requests
                "urllib3": {"enabled": True},  # Trace urllib3 requests
            },
        )

        # Enable Agent Framework instrumentation for workflow/executor tracing
        # This uses the global TracerProvider that Azure Monitor configured above
        # Note: This may cause "Failed to detach context" warnings in SSE streaming
        # scenarios, but the spans are still captured and exported correctly.
        enable_instrumentation(enable_sensitive_data=enable_sensitive)

        # Suppress the noisy context detach error logs (they're harmless warnings)
        logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)

        logger.info(
            "OpenTelemetry configured with Azure Monitor (sensitive_data=%s)", enable_sensitive
        )

    except ImportError:
        logger.warning(
            "azure-monitor-opentelemetry not installed. "
            "Install with: pip install azure-monitor-opentelemetry"
        )
        # Fall back to OTLP exporters
        _configure_otlp_exporters()


def _configure_otlp_exporters() -> None:
    """Configure OTLP exporters for local development (Aspire Dashboard, Jaeger, etc.)."""
    from agent_framework.observability import create_resource, enable_instrumentation
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    enable_sensitive = os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() == "true"
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    # Create resource and tracer provider
    resource = create_resource()
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint is configured
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Optionally add console exporter for debugging
    if os.getenv("ENABLE_CONSOLE_EXPORTERS", "false").lower() == "true":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Enable Agent Framework instrumentation
    enable_instrumentation(enable_sensitive_data=enable_sensitive)

    # Suppress the noisy context detach error logs (they're harmless warnings)
    logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)

    logger.info("OpenTelemetry configured with OTLP exporters (endpoint=%s)", otlp_endpoint)
