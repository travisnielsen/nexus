from __future__ import annotations

# ============================================================================
# IMPORTANT: Import patches FIRST before any other imports
# This applies critical workarounds for pydantic and deepcopy issues.
# See patches.py for details on the issues being fixed.
# ============================================================================
import patches  # noqa: F401 - side effects only

import json
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional, Any
from pathlib import Path

import uvicorn
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Query
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from agents import create_logistics_agent  # type: ignore
from agent_framework._clients import ChatClientProtocol
from middleware import (  # type: ignore
    ResponsesApiThreadMiddleware,
    azure_scheme,
    azure_ad_settings,
    AzureADAuthMiddleware,
)
from monitoring import configure_observability, is_observability_enabled  # type: ignore

load_dotenv()

# Configure logging to show INFO level from our modules
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)
# Reduce noise from azure/httpx libraries
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
# Reduce fastapi_azure_auth verbosity
logging.getLogger("fastapi_azure_auth").setLevel(logging.WARNING)
# Control agent_framework verbosity via AGENT_FRAMEWORK_LOG_LEVEL env var (default: WARNING)
agent_framework_log_level = os.getenv("AGENT_FRAMEWORK_LOG_LEVEL", "WARNING").upper()
logging.getLogger("agent_framework").setLevel(getattr(logging, agent_framework_log_level, logging.WARNING))
logging.getLogger("agent_framework_ag_ui").setLevel(getattr(logging, agent_framework_log_level, logging.WARNING))

logger = logging.getLogger(__name__)

# Check if Azure AD authentication is configured and enabled
AUTH_CONFIGURED = bool(
    azure_ad_settings.AZURE_AD_CLIENT_ID 
    and azure_ad_settings.AZURE_AD_TENANT_ID
    and azure_ad_settings.AUTH_ENABLED
)

# Configure observability before creating the app
configure_observability()

# These will be initialized in the lifespan handler
chat_client: ChatClientProtocol = None  # type: ignore
logistics_agent = None  # type: ignore


async def _init_chat_client():
    """Initialize chat client and agent asynchronously.
    
    This is called during application startup.
    """
    global chat_client, logistics_agent
    
    # Build the Responses API client
    from clients import build_responses_client  # type: ignore
    chat_client = build_responses_client()
    
    # Add the Responses API middleware
    logger.info("Using Responses API with ResponsesApiThreadMiddleware")
    chat_client.middleware = [ResponsesApiThreadMiddleware()]
    
    logistics_agent = create_logistics_agent(chat_client)


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
        agent=logistics_agent,
        path="/logistics",
    )
    logger.info("Registered AG-UI endpoint at /logistics")
    
    # Log observability status
    if is_observability_enabled():
        logger.info("OpenTelemetry observability is ENABLED")
    else:
        logger.info("OpenTelemetry observability is disabled (set ENABLE_INSTRUMENTATION=true to enable)")
    
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
    } if AUTH_CONFIGURED else None,
)

# IMPORTANT: Middleware runs in reverse order of addition
# CORS must be added AFTER auth so it runs FIRST (handles preflight before auth)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# REST Data Endpoints for Bulk Data Loading
# These endpoints provide fast data access without SSE overhead
# ============================================================================

# MCP client imports for data loading (HTTP-based)
from agents.utils import (
    get_flights_from_mcp,
    get_flight_by_id_from_mcp,
    get_flight_summary_from_mcp,
    get_historical_from_mcp,
)


# ============================================================================
# Feedback Models
# ============================================================================

class RecommendationFeedbackPayload(BaseModel):
    """Feedback payload for risk mitigation recommendations."""
    flightId: str
    flightNumber: str
    votes: dict[str, str]  # recommendation_id -> "up" | "down"
    comment: Optional[str] = None
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


@app.get("/logistics/data/flights", response_model=FlightsResponse)
async def get_flights(
    limit: int = Query(100, ge=1, le=200, description="Maximum number of flights to return"),
    offset: int = Query(0, ge=0, description="Number of flights to skip"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: low, medium, high, critical"),
    utilization: Optional[str] = Query(None, description="Filter by utilization: over (>95%), near_capacity (85-95%), optimal (50-85%), under (<50%)"),
    route_from: Optional[str] = Query(None, description="Filter by origin airport code"),
    route_to: Optional[str] = Query(None, description="Filter by destination airport code"),
    date_from: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    sort_by: Optional[str] = Query("utilizationPercent", description="Sort field"),
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
        }
    )


@app.get("/logistics/data/flights/{flight_id}")
async def get_flight_by_id_endpoint(flight_id: str):
    """Get a specific flight by ID or flight number.
    
    Data is loaded from MCP server via HTTP.
    """
    return await get_flight_by_id_from_mcp(flight_id)


@app.get("/logistics/data/historical", response_model=HistoricalResponse)
async def get_historical_data(
    route_from: Optional[str] = Query(None, description="Filter by origin airport code"),
    route_to: Optional[str] = Query(None, description="Filter by destination airport code"),
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
        }
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
