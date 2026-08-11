"""Content-block helpers for the FreeCAD tools (ported from freecad-mcp responses.py, MIT).

Same shapes as the rest of FreeGLM: plain dicts, not SDK objects. The addon returns a
screenshot as a base64 PNG string, which is exactly what an image content block's `data` wants.
"""

from __future__ import annotations

import json
from typing import Any

from shared.content import image


def text_response(message: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": message}]


def json_response(data: Any) -> list[dict[str, Any]]:
    return text_response(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def add_screenshot_if_available(
    response: list[dict[str, Any]],
    screenshot: str | None,
    only_text_feedback: bool,
) -> list[dict[str, Any]]:
    if only_text_feedback or not screenshot:
        return response
    return [*response, image(screenshot, "image/png")]
