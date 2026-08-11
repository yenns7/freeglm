"""MCP tool: check if Hyper3D Rodin integration is enabled in Blender."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Hyper3DStatusArgs(BaseModel):
    pass


TOOL: dict[str, Any] = {
    "name": "get_hyper3d_status",
    "description": (
        "Check if Hyper3D Rodin integration is enabled in Blender. "
        "Returns a message indicating whether Hyper3D Rodin features are available."
    ),
    "args": Hyper3DStatusArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_blender.loader import get_connection

    try:
        result = get_connection().send_command("get_hyper3d_status")
        message = result.get("message", "")
        return [{"type": "text", "text": message}]
    except Exception as e:
        return [{"type": "text", "text": f"Error checking Hyper3D status: {e}"}]
