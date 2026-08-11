"""Example tool (TEXT return): echo a message back."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from shared.content import text


class EchoArgs(BaseModel):
    message: str = Field(description="Text to echo back.")
    repeat: int = Field(default=1, description="How many times to repeat the message (1-10).")


TOOL: dict[str, Any] = {
    "name": "echo",
    "description": "Echo a message back as text. Demonstrates a text-only tool.",
    "args": EchoArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    message = arguments.get("message", "")
    repeat = max(1, min(int(arguments.get("repeat", 1)), 10))
    return [text("\n".join([message] * repeat))]
