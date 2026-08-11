"""MCP tool: check whether PolyHaven integration is enabled in Blender (text return)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PolyhavenStatusArgs(BaseModel):
    pass


TOOL: dict[str, Any] = {
    "name": "get_polyhaven_status",
    "description": (
        "Check if PolyHaven integration is enabled in Blender. "
        "Returns a message indicating whether PolyHaven features are available."
    ),
    "args": PolyhavenStatusArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_blender.loader import get_connection

    try:
        result = get_connection().send_command("get_polyhaven_status")
        enabled = result.get("enabled", False)
        message = result.get("message", "")
        if enabled:
            message += "PolyHaven is good at Textures, and has a wider variety of textures than Sketchfab."
        return [{"type": "text", "text": message}]
    except Exception as e:
        return [{"type": "text", "text": f"Error checking PolyHaven status: {e}"}]
