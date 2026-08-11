"""Render PDF pages as image + text content blocks via pypdfium2 (raster + text)."""

from __future__ import annotations

from typing import Any

from freeglm_core.renderers import DEFAULT_MAX_PAGES, parse_pages
from shared.env import IMAGE_BUDGET_TOKENS, IMAGE_MIN_PIXELS, MAX_RESPONSE_BYTES
from shared.image import budget_to_pixels, process_image


def render(path: str, **opts: Any) -> list[dict[str, Any]]:
    """Render document pages as MCP content blocks (image + extracted text per page)."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        raise RuntimeError('Missing dependency — install with: pip install "freeglm[viz]"')

    dpi = opts.get("dpi", 150)
    max_pages = opts.get("max_pages", DEFAULT_MAX_PAGES)
    budget = opts.get("budget", "large")
    max_pixels = budget_to_pixels(budget, IMAGE_BUDGET_TOKENS)

    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    doc_type = opts.get("doc_type") or ext.upper() or "DOC"

    doc = pdfium.PdfDocument(path)
    try:
        total = len(doc)

        pages_str = opts.get("pages")
        if pages_str:
            page_indices = parse_pages(pages_str, total)
        else:
            page_indices = list(range(min(total, max_pages)))

        # Cap pages to keep response under MAX_RESPONSE_BYTES.
        max_safe = max(1, int(MAX_RESPONSE_BYTES / (max_pixels * 0.3)))
        page_indices = page_indices[:max_safe]

        page_texts = _extract_page_texts(doc, page_indices)

        blocks: list[dict[str, Any]] = [{"type": "text", "text": f"[{doc_type} Start]"}]
        blocks.append({"type": "text", "text": f"Total pages: {total} | Showing pages: {_format_range(page_indices)}"})
        # Point at cached PDF so model can re-read without re-converting.
        cache_path = opts.get("cache_path")
        if cache_path:
            blocks.append(
                {
                    "type": "text",
                    "text": f"Rendered PDF cached at: {cache_path} "
                    f"(re-read other pages via visualize/read_image with this path — no re-render)",
                }
            )
        for idx in page_indices:
            block, w, h = _page_image_block(doc[idx], dpi, max_pixels)
            blocks.append({"type": "text", "text": f"[Page {idx + 1} View] {h}x{w} (HxW)"})
            blocks.append(block)
            page_text = page_texts.get(idx, "").strip()
            if page_text:
                blocks.append({"type": "text", "text": f"[Page {idx + 1} Extracted Text]\n{page_text}"})
        blocks.append({"type": "text", "text": f"[{doc_type} End]"})
        return blocks
    finally:
        doc.close()


def _page_image_block(page, dpi: int, max_pixels: int) -> tuple[dict[str, Any], int, int]:
    """Rasterize one pypdfium2 page; return (image block, w, h)."""
    from shared.image import render_pdf_page

    img = render_pdf_page(page, dpi)
    _, b64, w, h, mime = process_image(img, IMAGE_MIN_PIXELS, max_pixels)
    return {"type": "image", "data": b64, "mimeType": mime}, w, h


def _extract_page_texts(doc, page_indices: list[int]) -> dict[int, str]:
    """Extract each page's text layer (0-based keys) via pypdfium2's text API.

    Reuses the already-open document (no second file open) — same PDFium backend as rendering.
    """
    texts: dict[int, str] = {}
    total = len(doc)
    for idx in page_indices:
        if not (0 <= idx < total):
            continue
        try:
            textpage = doc[idx].get_textpage()
            try:
                text = textpage.get_text_bounded()
            finally:
                textpage.close()
        except Exception:
            continue
        if text and text.strip():
            texts[idx] = text
    return texts


def _format_range(indices: list[int]) -> str:
    """Format 0-based page indices as a compact 1-based range, e.g. [0,1,2,4] -> "1-3, 5"."""
    if not indices:
        return ""
    groups: list[list[int]] = []
    for idx in sorted(indices):
        page = idx + 1
        if groups and page == groups[-1][-1] + 1:
            groups[-1].append(page)
        else:
            groups.append([page])
    return ", ".join(str(g[0]) if len(g) == 1 else f"{g[0]}-{g[-1]}" for g in groups)
