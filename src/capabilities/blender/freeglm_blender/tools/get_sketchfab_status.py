"""MCP tool: check whether Sketchfab integration is enabled in Blender (text return)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SketchfabStatusArgs(BaseModel):
    pass


TOOL: dict[str, Any] = {
    "name": "get_sketchfab_status",
    "description": (
        "Check if Sketchfab integration is enabled in Blender. "
        "Returns a message indicating whether Sketchfab features are available."
    ),
    "args": SketchfabStatusArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_blender.loader import get_connection

    try:
        result = get_connection().send_command("get_sketchfab_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += "Sketchfab is good at Realistic models, and has a wider variety of models than PolyHaven."
        return [{"type": "text", "text": message}]
    except Exception as e:
        return [{"type": "text", "text": f"Error checking Sketchfab status: {e}"}]
