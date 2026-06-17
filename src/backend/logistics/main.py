from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from agent_framework import SupportsChatGetResponse
from agent_framework_ag_ui import AgentFrameworkAgent, add_agent_framework_fastapi_endpoint
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================================
# IMPORTANT: Import patches FIRST before any other imports
# This applies critical workarounds for pydantic and deepcopy issues.
# See patches.py for details on the issues being fixed.
# ============================================================================
import patches  # noqa: F401 - side effects only
from agents import create_logistics_agent, ensure_foundry_agent_exists  # type: ignore
from agents.tools.trace_helpers import validate_trace_identity_payload
from agents.utils import (
    SessionBlockedResponse,
    SessionListResponse,
    SessionLoadResponse,
    SessionMutationResult,
    SessionRenameRequest,
    TraceIdentityHeaders,
    clear_trace_identity,
    get_flight_by_id_from_mcp,
    get_flight_summary_from_mcp,
    get_flights_from_mcp,
    get_historical_from_mcp,
    get_trace_identity,
    set_trace_identity,
)
from middleware import (  # type: ignore
    AzureADAuthMiddleware,
    azure_ad_settings,
    azure_scheme,
)
from monitoring import configure_observability, is_observability_enabled  # type: ignore
from services import SessionMetadataStoreUnavailableError, SessionService, create_session_service

load_dotenv()

# Configure logging to show INFO level from our modules
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
# Reduce noise from azure/httpx libraries
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
# Reduce fastapi_azure_auth verbosity
logging.getLogger("fastapi_azure_auth").setLevel(logging.WARNING)
# Control agent_framework verbosity via AGENT_FRAMEWORK_LOG_LEVEL env var (default: WARNING)
agent_framework_log_level = os.getenv("AGENT_FRAMEWORK_LOG_LEVEL", "WARNING").upper()
logging.getLogger("agent_framework").setLevel(
    getattr(logging, agent_framework_log_level, logging.WARNING)
)
logging.getLogger("agent_framework_ag_ui").setLevel(
    getattr(logging, agent_framework_log_level, logging.WARNING)
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("logistics.api")

# Check if Azure AD authentication is configured and enabled
AUTH_CONFIGURED = bool(
    azure_ad_settings.AZURE_AD_CLIENT_ID
    and azure_ad_settings.AZURE_AD_TENANT_ID
    and azure_ad_settings.AUTH_ENABLED
)

# Configure observability before creating the app
configure_observability()

# These will be initialized in the lifespan handler
chat_client: SupportsChatGetResponse | None = None
logistics_agent: AgentFrameworkAgent | None = None
session_service: SessionService | None = None


async def _init_chat_client():
    """Initialize chat client and agent asynchronously.

    This is called during application startup.
    """
    global chat_client, logistics_agent, session_service

    # Build the Foundry chat client
    from clients import build_responses_client  # type: ignore

    chat_client = build_responses_client()

    # First deployment bootstrap: create Foundry agent if missing.
    await ensure_foundry_agent_exists(chat_client)

    logistics_agent = create_logistics_agent(chat_client)
    if azure_ad_settings.AUTH_ENABLED:
        session_service = create_session_service(chat_client)
        try:
            await session_service.ensure_metadata_store()
        except SessionMetadataStoreUnavailableError as exc:
            logger.warning(
                "Session metadata store unavailable during startup; continuing in degraded mode: %s",
                exc,
            )
    else:
        session_service = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Application lifespan handler.
    Initializes the chat client and loads Azure AD OpenID configuration.
    """
    global logistics_agent

    # Initialize chat client and agent
    await _init_chat_client()

    # Register the AG-UI endpoint now that logistics_agent is initialized
    # NOTE: This must happen here because the agent is created asynchronously
    add_agent_framework_fastapi_endpoint(
        app=_app,
        agent=logistics_agent,  # pyright: ignore[reportArgumentType]
        path="/logistics",
    )
    logger.info("Registered AG-UI endpoint at /logistics")

    # Log observability status
    if is_observability_enabled():
        logger.info("OpenTelemetry observability is ENABLED")
    else:
        logger.info(
            "OpenTelemetry observability is disabled (set ENABLE_INSTRUMENTATION=true to enable)"
        )

    # Log authentication status
    if not azure_ad_settings.AUTH_ENABLED:
        logger.warning("=" * 60)
        logger.warning("WARNING: Authentication is DISABLED via AUTH_ENABLED=false!")
        logger.warning("The API will respond to ANONYMOUS connections.")
        logger.warning("Do NOT use this setting in production.")
        logger.warning("=" * 60)
    elif AUTH_CONFIGURED:
        logger.info("Azure AD authentication is ENABLED")
        if azure_scheme:
            await azure_scheme.openid_config.load_config()
    else:
        logger.warning("=" * 60)
        logger.warning("WARNING: Azure AD authentication is NOT configured!")
        logger.warning("The API will respond to ANONYMOUS connections.")
        logger.warning("Set AZURE_AD_CLIENT_ID and AZURE_AD_TENANT_ID to enable auth.")
        logger.warning("=" * 60)
    yield

    # Shutdown: Cleanup
    logger.info("Application shutdown complete")


app = FastAPI(
    title="CopilotKit + Microsoft Agent Framework (Python)",
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": azure_ad_settings.AZURE_AD_CLIENT_ID,
    }
    if AUTH_CONFIGURED
    else None,
)


class TraceIdentityMiddleware(BaseHTTPMiddleware):
    """Extract and validate trace identity headers for request-scoped context."""

    async def dispatch(self, request: Request, call_next):
        header_payload = {
            "x_trace_conversation_id": request.headers.get("x-trace-conversation-id"),
            "x_trace_turn_id": request.headers.get("x-trace-turn-id"),
            "x_trace_run_id": request.headers.get("x-trace-run-id"),
            "x_trace_tool_call_id": request.headers.get("x-trace-tool-call-id"),
            "x_trace_a2a_interaction_id": request.headers.get("x-trace-a2a-interaction-id"),
        }

        try:
            parsed_headers = TraceIdentityHeaders.model_validate(header_payload)
            identity = parsed_headers.to_identity()
        except Exception as exc:
            clear_trace_identity()
            raise HTTPException(status_code=400, detail="Invalid trace identity headers") from exc

        set_trace_identity(identity)
        try:
            if request.url.path.startswith("/logistics"):
                conversation_id_for_seed = (
                    identity.conversation_id if identity and identity.conversation_id else None
                )
                if conversation_id_for_seed is None and request.method.upper() == "POST":
                    conversation_id_for_seed = (
                        await _extract_conversation_id_from_logistics_request(request)
                    )

                with tracer.start_as_current_span("turn.lifecycle") as span:
                    if identity:
                        span.set_attribute("gen_ai.conversation.id", identity.conversation_id)
                        if identity.turn_id:
                            span.set_attribute("gen_ai.turn.id", identity.turn_id)
                        if identity.run_id:
                            span.set_attribute("gen_ai.run.id", identity.run_id)
                    response = await call_next(request)

                if (
                    request.method.upper() == "POST"
                    and response.status_code < 500
                    and conversation_id_for_seed
                ):
                    await _seed_session_metadata_for_turn(
                        request=request,
                        conversation_id=conversation_id_for_seed,
                    )
            else:
                response = await call_next(request)
            if identity:
                response.headers["x-trace-conversation-id"] = identity.conversation_id
                if identity.run_id:
                    response.headers["x-trace-run-id"] = identity.run_id
            return response
        finally:
            clear_trace_identity()


# IMPORTANT: Middleware runs in reverse order of addition
# CORS must be added AFTER auth so it runs FIRST (handles preflight before auth)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TraceIdentityMiddleware)

# Add Azure AD auth middleware only if configured
# This runs AFTER CORS, so preflight OPTIONS requests are handled first
if AUTH_CONFIGURED:
    app.add_middleware(AzureADAuthMiddleware, settings=azure_ad_settings)


# Protected health check endpoint (example of how to use auth)
@app.get("/health")
async def health_check():
    """Unprotected health check endpoint."""
    return {"status": "healthy"}


@app.get("/me")
async def get_current_user(request: Request):
    """
    Protected endpoint that returns the current user's claims.
    Requires a valid Azure AD token (validated by middleware).
    """
    user = getattr(request.state, "user", None)
    if not user:
        return {"error": "Azure AD authentication not configured or user not authenticated"}
    return {
        "claims": user,
        "name": user.get("name"),
        "email": user.get("preferred_username"),
    }


# ============================================================================
# Conversation Management Endpoint
# Creates Azure Foundry conversations for session continuity
# ============================================================================


@app.post("/api/conversations")
async def create_conversation(request: Request):
    """Create a new Azure Foundry conversation.

    Returns a conv_* ID that the frontend uses as the CopilotKit threadId.
    With use_service_session=True, the AG-UI framework passes this ID as
    service_session_id to AgentSession, and Foundry conversation history uses it as
    the conversation parameter for server-side history management.
    """
    if chat_client is None:
        raise ValueError("Chat client not initialized")

    try:
        # get_openai_client() is synchronous — returns an AsyncOpenAI instance
        openai_client = chat_client.project_client.get_openai_client()  # pyright: ignore[reportAttributeAccessIssue]
        conversation = await openai_client.conversations.create()

        logger.info("Created Azure Foundry conversation: %s", conversation.id)

        validate_trace_identity_payload({"conversation_id": conversation.id})

        return {"conversationId": conversation.id}
    except Exception as e:
        logger.error("Failed to create conversation: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# REST Data Endpoints for Bulk Data Loading
# These endpoints provide fast data access without SSE overhead
# ============================================================================

# ============================================================================
# Feedback Models
# ============================================================================


class RecommendationFeedbackPayload(BaseModel):
    """Feedback payload for risk mitigation recommendations."""

    flightId: str
    flightNumber: str
    votes: dict[str, str]  # recommendation_id -> "up" | "down"
    comment: str | None = None
    timestamp: str


class FlightsResponse(BaseModel):
    """Response model for flights endpoint."""

    flights: list[dict]
    total: int
    query: dict


class HistoricalResponse(BaseModel):
    """Response model for historical data endpoint."""

    historicalData: list[dict]
    routes: list[str]
    total: int
    query: dict


def _get_session_service() -> SessionService:
    if not azure_ad_settings.AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Session APIs are disabled")
    if session_service is None:
        raise HTTPException(status_code=503, detail="Session service is not initialized")
    return session_service


async def _extract_conversation_id_from_logistics_request(request: Request) -> str | None:
    """Best-effort extraction of conversation/thread ID from AG-UI request payload."""

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type.lower():
        return None

    try:
        payload = await request.json()
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    for key in ("threadId", "thread_id", "conversationId", "conversation_id"):
        candidate = payload.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


async def _seed_session_metadata_for_turn(request: Request, conversation_id: str) -> None:
    """Persist session metadata when the first real turn reaches the logistics endpoint."""

    if not azure_ad_settings.AUTH_ENABLED:
        return

    try:
        user_id = _get_user_id_for_session_scope(request)
    except HTTPException:
        # If auth context is unavailable for a turn request, skip metadata writes.
        return

    try:
        await _get_session_service().seed_session_metadata(
            user_id=user_id,
            session_id=conversation_id,
        )
    except SessionMetadataStoreUnavailableError:
        logger.warning(
            "Session metadata store unavailable while seeding turn metadata; "
            "continuing without history metadata for conversation_id=%s user_id=%s",
            conversation_id,
            user_id,
        )
    except Exception:
        logger.exception(
            "Failed to seed turn metadata for conversation_id=%s user_id=%s",
            conversation_id,
            user_id,
        )


def _get_user_id_for_session_scope(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if AUTH_CONFIGURED and not isinstance(user, dict):
        raise HTTPException(status_code=401, detail="Authentication required for session APIs")
    if isinstance(user, dict):
        return (
            user.get("oid")
            or user.get("sub")
            or user.get("preferred_username")
            or user.get("name")
            or "anonymous"
        )
    return "anonymous"


@app.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions(request: Request):
    """Session list route shell (Phase 2 foundation)."""

    service = _get_session_service()
    user_id = _get_user_id_for_session_scope(request)
    try:
        return await service.list_sessions(user_id=user_id, limit=20)
    except SessionMetadataStoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    "/api/sessions/{session_id}",
    response_model=SessionLoadResponse | SessionBlockedResponse,
)
async def load_session(session_id: str, request: Request):
    """Session load route shell (Phase 2 foundation)."""

    service = _get_session_service()
    user_id = _get_user_id_for_session_scope(request)
    try:
        return await service.load_session(user_id=user_id, session_id=session_id)
    except SessionMetadataStoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.patch("/api/sessions/{session_id}", response_model=SessionMutationResult)
async def rename_session(session_id: str, payload: SessionRenameRequest, request: Request):
    """Session rename route shell (Phase 2 foundation)."""

    service = _get_session_service()
    user_id = _get_user_id_for_session_scope(request)
    try:
        result = await service.rename_session(
            user_id=user_id, session_id=session_id, title=payload.title
        )
    except SessionMetadataStoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result.status.value == "rejected":
        raise HTTPException(status_code=409, detail=result.conflict_reason or "Rename rejected")
    return result


@app.delete("/api/sessions/{session_id}", response_model=SessionMutationResult)
async def delete_session(session_id: str, request: Request):
    """Session delete route shell (Phase 2 foundation)."""

    service = _get_session_service()
    user_id = _get_user_id_for_session_scope(request)
    try:
        result = await service.delete_session(user_id=user_id, session_id=session_id)
    except SessionMetadataStoreUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result.status.value == "rejected":
        raise HTTPException(status_code=409, detail=result.conflict_reason or "Delete rejected")
    return result


@app.get("/logistics/data/flights", response_model=FlightsResponse)
async def get_flights(
    limit: int = Query(100, ge=1, le=200, description="Maximum number of flights to return"),
    offset: int = Query(0, ge=0, description="Number of flights to skip"),
    risk_level: str | None = Query(
        None, description="Filter by risk level: low, medium, high, critical"
    ),
    utilization: str | None = Query(
        None,
        description="Filter by utilization: over (>95%), near_capacity (85-95%), optimal (50-85%), under (<50%)",
    ),
    route_from: str | None = Query(None, description="Filter by origin airport code"),
    route_to: str | None = Query(None, description="Filter by destination airport code"),
    date_from: str | None = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    sort_by: str | None = Query("utilizationPercent", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
):
    """
    REST endpoint for bulk flight data retrieval.

    This endpoint provides fast data access for initial page load and
    agent-triggered queries without SSE overhead.

    Data is loaded from MCP server via HTTP.
    """
    mcp_result = await get_flights_from_mcp(
        limit=limit,
        offset=offset,
        risk_level=risk_level,
        utilization=utilization,
        route_from=route_from,
        route_to=route_to,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by or "utilizationPercent",
        sort_desc=sort_desc,
    )

    flights = mcp_result.get("flights", [])
    total = mcp_result.get("total", len(flights))

    return FlightsResponse(
        flights=flights,
        total=total,
        query={
            "limit": limit,
            "offset": offset,
            "risk_level": risk_level,
            "utilization": utilization,
            "route_from": route_from,
            "route_to": route_to,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@app.get("/logistics/data/flights/{flight_id}")
async def get_flight_by_id_endpoint(flight_id: str):
    """Get a specific flight by ID or flight number.

    Data is loaded from MCP server via HTTP.
    """
    return await get_flight_by_id_from_mcp(flight_id)


@app.get("/logistics/data/historical", response_model=HistoricalResponse)
async def get_historical_data(
    route_from: str | None = Query(None, description="Filter by origin airport code"),
    route_to: str | None = Query(None, description="Filter by destination airport code"),
    days: int = Query(10, ge=1, le=30, description="Number of days of data"),
    include_predictions: bool = Query(True, description="Include predicted data"),
):
    """
    REST endpoint for historical payload data retrieval.
    Proxies to the MCP server's /api/historical endpoint.
    """
    # Build route filter if both from/to are specified
    route = None
    if route_from and route_to:
        route = f"{route_from.upper()} → {route_to.upper()}"

    # Fetch from MCP server
    mcp_response = await get_historical_from_mcp(
        days=days,
        route=route,
        include_predictions=include_predictions,
    )

    # Transform MCP response to match frontend expected format
    # MCP returns separate "historical" and "predictions" arrays
    # Frontend expects a single "historicalData" array with predicted flag on each item
    historical = mcp_response.get("historical", [])
    predictions = mcp_response.get("predictions", [])

    # Combine historical (sorted ascending by date) and predictions
    historical_sorted = sorted(historical, key=lambda x: x.get("date", ""))
    combined_data = historical_sorted + predictions

    # Extract unique routes
    routes = sorted(set(d.get("route", "") for d in combined_data if d.get("route")))

    return HistoricalResponse(
        historicalData=combined_data,
        routes=routes,
        total=len(combined_data),
        query={
            "route_from": route_from,
            "route_to": route_to,
            "days": days,
            "include_predictions": include_predictions,
        },
    )


@app.get("/logistics/data/summary")
async def get_data_summary():
    """
    Get a summary of all available data for LLM context.
    Returns counts and statistics without full data.
    Proxies to the MCP server's /api/summary endpoint.
    """
    return await get_flight_summary_from_mcp()


# ============================================================================
# Feedback Endpoint
# ============================================================================


@app.post("/logistics/feedback")
async def submit_recommendation_feedback(payload: RecommendationFeedbackPayload):
    """
    Submit feedback on risk mitigation recommendations.

    Currently logs feedback for analysis. Backend storage will be implemented later.
    """
    identity = get_trace_identity()
    if identity:
        validate_trace_identity_payload(identity.model_dump())

    logger.info("=" * 60)
    logger.info("RECOMMENDATION FEEDBACK RECEIVED")
    logger.info("=" * 60)
    logger.info("Flight ID: %s", payload.flightId)
    logger.info("Flight Number: %s", payload.flightNumber)
    logger.info("Timestamp: %s", payload.timestamp)
    logger.info("Votes: %s", json.dumps(payload.votes, indent=2))
    if payload.comment:
        logger.info("Comment: %s", payload.comment)
    logger.info("=" * 60)

    # TODO: Persist feedback to database/storage
    # For now, just acknowledge receipt

    return {
        "status": "received",
        "message": "Feedback logged successfully. Thank you!",
        "flightNumber": payload.flightNumber,
        "votesReceived": len(payload.votes),
    }


# NOTE: AG-UI endpoint for logistics_agent is registered in the lifespan handler
# This is because the agent is created asynchronously to allow existing agent lookup


if __name__ == "__main__":
    host = os.getenv("AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("AGENT_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
