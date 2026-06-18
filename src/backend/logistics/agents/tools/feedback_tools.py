"""Feedback tools for AG-UI overall feedback card flows."""

from __future__ import annotations

from uuid import uuid4
from typing import Annotated

from agent_framework import tool
from pydantic import Field


@tool(
    name="show_overall_feedback_card",
    description=(
        "Render an in-chat overall experience feedback card. "
        "Always use this when a user asks to share chat feedback, says they want to give feedback, "
        "or clicks a Feedback suggestion. Do not ask a follow-up question first."
    ),
    schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": ["string", "null"],
                "description": (
                    "Optional card prompt text shown to the user. "
                    "If omitted, defaults to a generic overall experience prompt."
                ),
            }
        },
        "required": ["prompt"],
        "additionalProperties": False,
    },
)
async def show_overall_feedback_card(
    prompt: Annotated[
        str | None,
        Field(
            description=(
                "Optional card prompt text shown to the user. "
                "If omitted, defaults to a generic overall experience prompt."
            )
        ),
    ] = None,
) -> dict[str, object]:
    return {
        "feedback_kind": "overall_experience",
        "source_surface": "overall_feedback_card",
        "card_turn_id": f"feedback_{uuid4().hex}",
        "prompt": prompt or "How was your overall experience with this application?",
    }
