"""MCP tool: screenshot the FreeCAD active view from a named angle (image return)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class GetViewArgs(BaseModel):
    view_name: Literal["Isometric", "Front", "Top", "Right", "Back", "Left", "Bottom", "Dimetric", "Trimetric"] = Field(
        description="The standard view angle to capture."
    )
    width: Optional[int] = Field(default=None, description="Screenshot width in px (default: viewport width).")
    height: Optional[int] = Field(default=None, description="Screenshot height in px (default: viewport height).")
    focus_object: Optional[str] = Field(
        default=None, description="Name of an object to focus on (default: fit all objects in view)."
    )


TOOL: dict[str, Any] = {
    "name": "get_view",
    "description": "Get a screenshot of the FreeCAD active view from a named standard angle.",
    "args": GetViewArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_freecad._responses import text_response
    from freeglm_freecad.loader import get_connection
    from shared.content import image

    conn = get_connection()
    screenshot = conn.get_active_screenshot(
        arguments.get("view_name", "Isometric"),
        arguments.get("width"),
        arguments.get("height"),
        arguments.get("focus_object"),
    )
    if screenshot:
        return [image(screenshot, "image/png")]
    return text_response("Cannot get screenshot in the current view type (such as TechDraw or Spreadsheet)")
