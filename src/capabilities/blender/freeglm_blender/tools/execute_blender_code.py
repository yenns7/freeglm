"""MCP tool: execute arbitrary Python inside the running Blender (the primary modeling tool)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExecuteBlenderCodeArgs(BaseModel):
    code: str = Field(description="The Python code to execute inside Blender (the `bpy` module is available).")


TOOL: dict[str, Any] = {
    "name": "execute_blender_code",
    "description": (
        "Execute arbitrary Python code in the running Blender (bpy). This is the PRIMARY tool for "
        "modeling: create/edit geometry, modifiers, materials, lighting, cameras, and rendering. "
        "Make sure to do it step-by-step by breaking complex work into smaller chunks."
    ),
    "args": ExecuteBlenderCodeArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_blender.loader import get_connection

    code = arguments.get("code", "")
    try:
        result = get_connection().send_command("execute_code", {"code": code})
        return [{"type": "text", "text": f"Code executed successfully: {result.get('result', '')}"}]
    except Exception as e:
        return [{"type": "text", "text": f"Error executing code: {e}"}]
