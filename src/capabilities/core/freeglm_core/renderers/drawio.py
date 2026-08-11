"""Render DrawIO (.drawio) diagrams to images via SVG extraction + resvg (resvg-py)."""

from __future__ import annotations

import base64
import urllib.parse
import zlib
from typing import Any


def render(path: str, **opts: Any) -> list:
    try:
        from lxml import etree
    except ImportError:
        raise RuntimeError('Missing dependency — install with: pip install "freeglm[viz]"')

    from freeglm_core.renderers import DEFAULT_MAX_PAGES, labeled_image, parse_pages

    tree = etree.parse(path)
    root = tree.getroot()

    diagrams = root.findall(".//diagram")
    if not diagrams:
        raise ValueError("No diagrams found in DrawIO file")

    pages = opts.get("pages")
    indices = (
        parse_pages(pages, len(diagrams))
        if pages
        else range(min(len(diagrams), opts.get("max_pages", DEFAULT_MAX_PAGES)))
    )
    budget = opts.get("budget", "large")
    content: list[dict[str, Any]] = []

    for i in indices:
        diagram = diagrams[i]
        svg_content = _diagram_to_svg(diagram)
        if svg_content:
            imgs = _svg_to_images(svg_content)
            name = diagram.get("name", f"Diagram {i + 1}")
            for img in imgs:
                content.extend(labeled_image(f"[{name}]", img, budget))

    if not content:
        raise ValueError("Failed to extract renderable content from DrawIO file")

    return content


def _diagram_to_svg(diagram) -> str | None:
    """Extract diagram content and convert to SVG."""
    from lxml import etree

    text = (diagram.text or "").strip()
    if not text:
        mx = diagram.find(".//mxGraphModel")
        if mx is not None:
            return _mxgraph_to_svg(mx)
        return None

    try:
        decoded = base64.b64decode(text)
        xml_str = zlib.decompress(decoded, -zlib.MAX_WBITS).decode("utf-8")
    except Exception:
        try:
            xml_str = urllib.parse.unquote(text)
        except Exception:
            return None

    try:
        inner = etree.fromstring(xml_str.encode("utf-8"))
        if inner.tag == "mxGraphModel":
            return _mxgraph_to_svg(inner)
    except Exception:
        pass

    return None


def _mxgraph_to_svg(mx_model) -> str:
    """Convert mxGraphModel XML to a basic SVG representation."""
    cells = mx_model.findall(".//mxCell")

    svg_elements = []
    max_x, max_y = 100, 100

    for cell in cells:
        geom = cell.find("mxGeometry")
        if geom is None:
            continue

        x = float(geom.get("x", 0))
        y = float(geom.get("y", 0))
        w = float(geom.get("width", 0))
        h = float(geom.get("height", 0))

        max_x = max(max_x, x + w + 20)
        max_y = max(max_y, y + h + 20)

        style = cell.get("style", "")
        label = cell.get("value", "")
        is_edge = cell.get("edge") == "1"

        if is_edge:
            source_x = x
            source_y = y
            target_x = x + w if w else x + 100
            target_y = y + h if h else y
            svg_elements.append(
                f'<line x1="{source_x}" y1="{source_y}" x2="{target_x}" y2="{target_y}" '
                f'stroke="#333" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
        elif w > 0 and h > 0:
            fill = "#ffffff"
            stroke = "#333333"
            if "rounded=1" in style:
                svg_elements.append(
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" ry="8" '
                    f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
                )
            elif "ellipse" in style:
                cx, cy = x + w / 2, y + h / 2
                svg_elements.append(
                    f'<ellipse cx="{cx}" cy="{cy}" rx="{w / 2}" ry="{h / 2}" '
                    f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
                )
            elif "rhombus" in style:
                points = f"{x + w / 2},{y} {x + w},{y + h / 2} {x + w / 2},{y + h} {x},{y + h / 2}"
                svg_elements.append(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
            else:
                svg_elements.append(
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                    f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
                )

            if label:
                from xml.sax.saxutils import escape

                tx = x + w / 2
                ty = y + h / 2
                font_size = min(14, max(8, int(h * 0.3)))
                svg_elements.append(
                    f'<text x="{tx}" y="{ty}" text-anchor="middle" dominant-baseline="central" '
                    f'font-family="sans-serif" font-size="{font_size}">{escape(label)}</text>'
                )

    arrow_marker = (
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#333"/></marker></defs>'
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{max_x}" height="{max_y}" '
        f'viewBox="0 0 {max_x} {max_y}">'
        f"{arrow_marker}"
        f'<rect width="100%" height="100%" fill="white"/>'
        f"{''.join(svg_elements)}"
        f"</svg>"
    )
    return svg


def _svg_to_images(svg_content: str) -> list:
    """Render SVG string to PIL Images via resvg."""
    from shared.image import svg_to_image

    return [svg_to_image(svg_string=svg_content, dpi=150)]
