"""MCP tool: list the open documents in the running FreeCAD."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ListDocumentsArgs(BaseModel):
    pass


TOOL: dict[str, Any] = {
    "name": "list_documents",
    "description": "Get the list of open documents in FreeCAD. Returns a list of document names.",
    "args": ListDocumentsArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_freecad._responses import json_response, text_response
    from freeglm_freecad.loader import get_connection

    try:
        conn = get_connection()
        return json_response(conn.list_documents())
    except Exception as e:
        return text_response(f"Failed to list documents: {e}")
