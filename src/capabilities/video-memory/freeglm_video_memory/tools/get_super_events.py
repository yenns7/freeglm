"""MCP tool: list super events (high-level narrative arcs)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from . import VideoPath


class GetSuperEventsArgs(BaseModel):
    video_path: VideoPath = None


TOOL: dict[str, Any] = {
    "name": "get_super_events",
    "description": (
        "List all Super Events (high-level narrative arcs). Each entry has: "
        "super_id, label, time_range, key_entities, description, num_macros. "
        "When to use: You need to understand the overall structure of the video, "
        "identify which story arc is relevant, or the user asks about the video's "
        "main sections or chapters."
    ),
    "args": GetSuperEventsArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_video_memory.loader import get_toolkit

    args = dict(arguments or {})
    toolkit = get_toolkit(args.pop("video_path", None))
    result = toolkit.get_super_events()
    return [{"type": "text", "text": result}]
