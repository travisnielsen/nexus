"""Minimal type stubs for agent-framework-a2a (pre-release, no py.typed marker)."""

from typing import Any, Sequence

class MessageContent:
    text: str

class Message:
    contents: list[MessageContent]

class AgentResponse:
    messages: list[Message]
    def __str__(self) -> str: ...

class A2AAgent:
    def __init__(
        self,
        *,
        name: str | None = ...,
        id: str | None = ...,
        description: str | None = ...,
        url: str | None = ...,
        timeout: float | None = ...,
        **kwargs: Any,
    ) -> None: ...

    async def run(
        self,
        messages: str | Sequence[str] | None = ...,
        **kwargs: Any,
    ) -> AgentResponse: ...
