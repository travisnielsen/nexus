"""
Recommendations Agent - A2A Server

This is a simple A2A-protocol agent that provides logistics recommendations.
It uses the a2a-sdk to host a proper A2A JSON-RPC endpoint.
"""

from __future__ import annotations

import os
import random
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Artifact,
    Part,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s"
)
logger = logging.getLogger(__name__)

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
    formatted = "\n".join([f"{i+1}. {rec}" for i, rec in enumerate(selected)])
    return f"Here are {num_recommendations} recommendations:\n\n{formatted}"


class RecommendationsAgentExecutor(AgentExecutor):
    """Simple agent executor that generates recommendations."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the agent and generate recommendations."""
        logger.info("Executing recommendations agent")
        
        # Extract the user message from the request
        user_message = ""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if isinstance(part, TextPart):
                    user_message = part.text
                    break
        
        logger.info(f"Received message: {user_message}")
        
        # Generate recommendations
        recommendations = generate_recommendations(3)
        
        # Create response message
        response_parts: list[Part] = [TextPart(text=recommendations)]
        
        # Create artifact with the response
        artifact = Artifact(
            artifact_id=str(uuid.uuid4()),
            parts=response_parts,
            name="recommendations",
            description="Logistics recommendations",
        )
        
        # Create completed task
        task = Task(
            id=context.task_id or "task-1",
            context_id=context.context_id or "context-1",
            status=TaskStatus(state=TaskState.completed),
            artifacts=[artifact],
        )
        
        # Send the completed task event
        await event_queue.enqueue_event(task)
        
        logger.info("Recommendations generated and sent")

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
        url="",  # Will be set by the A2A framework
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=capabilities,
        skills=[recommendations_skill],
    )


def create_a2a_app() -> A2AFastAPIApplication:
    """Create the A2A FastAPI application."""
    agent_card = create_agent_card()
    
    # Create the agent executor
    agent_executor = RecommendationsAgentExecutor()
    
    # Create task store for managing tasks
    task_store = InMemoryTaskStore()
    
    # Create the request handler
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
    )
    
    # Create the A2A application
    a2a_app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    
    return a2a_app


# Create FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for the FastAPI app."""
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


# Create and mount the A2A application at root (after health endpoint is defined)
a2a_app = create_a2a_app()
app.mount("/", a2a_app.build())


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5002"))
    logger.info(f"Starting Recommendations A2A Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
