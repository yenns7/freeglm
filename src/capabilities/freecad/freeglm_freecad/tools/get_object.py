"""MCP tool: get a single object from a FreeCAD document (JSON + optional screenshot)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GetObjectArgs(BaseModel):
    doc_name: str = Field(description="The name of the document to get the object from.")
    obj_name: str = Field(description="The name of the object to get.")


TOOL: dict[str, Any] = {
    "name": "get_object",
    "description": (
        "Get an object from a document. You can use this tool to get the properties of an object "
        "to see what you can check or edit. Returns the object and a screenshot of the object."
    ),
    "args": GetObjectArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_freecad._responses import (
        add_screenshot_if_available,
        json_response,
        text_response,
    )
    from freeglm_freecad.loader import get_connection, only_text_feedback

    doc_name = arguments.get("doc_name", "")
    obj_name = arguments.get("obj_name", "")
    only_text = only_text_feedback()
    try:
        conn = get_connection()
        response = json_response(conn.get_object(doc_name, obj_name))
        screenshot = None if only_text else conn.get_active_screenshot()
        return add_screenshot_if_available(response, screenshot, only_text)
    except Exception as e:
        return text_response(f"Failed to get object: {e}")
