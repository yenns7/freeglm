"""MCP tool: create a new document in the running FreeCAD."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateDocumentArgs(BaseModel):
    name: str = Field(description="The name of the document to create.")


TOOL: dict[str, Any] = {
    "name": "create_document",
    "description": (
        "Create a new document in FreeCAD. Returns a message indicating the success or "
        "failure of the document creation."
    ),
    "args": CreateDocumentArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_freecad._responses import text_response
    from freeglm_freecad.loader import get_connection

    name = arguments.get("name", "")
    try:
        conn = get_connection()
        res = conn.create_document(name)
        if res["success"]:
            return text_response(f"Document '{res['document_name']}' created successfully")
        return text_response(f"Failed to create document: {res['error']}")
    except Exception as e:
        return text_response(f"Failed to create document: {e}")
