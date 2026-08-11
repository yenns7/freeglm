"""MCP tool: get detailed information about a specific object in the Blender scene (JSON text return)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ObjectInfoArgs(BaseModel):
    object_name: str = Field(description="The name of the object to get information about.")


TOOL: dict[str, Any] = {
    "name": "get_object_info",
    "description": "Get detailed information about a specific object in the Blender scene.",
    "args": ObjectInfoArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    import json

    from freeglm_blender.loader import get_connection

    object_name = arguments.get("object_name", "")
    try:
        result = get_connection().send_command("get_object_info", {"name": object_name})
        return [{"type": "text", "text": json.dumps(result, indent=2)}]
    except Exception as e:
        return [{"type": "text", "text": f"Error getting object info: {e}"}]
