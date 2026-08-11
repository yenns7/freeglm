"""Render SVG files to an image content block via resvg (resvg-py)."""

from __future__ import annotations

from typing import Any


def render(path: str, **opts: Any) -> list[dict[str, Any]]:
    """Rasterize an SVG file to a single MCP image content block."""
    from freeglm_core.renderers import labeled_image
    from shared.image import svg_to_image

    dpi = opts.get("dpi", 150)
    budget = opts.get("budget", "large")
    doc_type = opts.get("doc_type") or "SVG"

    try:
        img = svg_to_image(svg_path=path, dpi=dpi)
    except ImportError:
        raise RuntimeError('Missing dependency — install with: pip install "freeglm[viz]"')

    blocks: list[dict[str, Any]] = [{"type": "text", "text": f"[{doc_type} Start]"}]
    blocks.extend(labeled_image("[SVG View]", img, budget))
    blocks.append({"type": "text", "text": f"[{doc_type} End]"})
    return blocks
