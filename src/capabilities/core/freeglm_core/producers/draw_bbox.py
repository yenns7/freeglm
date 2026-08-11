"""MCP tool: draw bounding boxes on an image and save the result."""

from __future__ import annotations

from typing import Annotated, Any, Optional

from pydantic import BaseModel, Field

from shared.content import default_output_path, require_dep, require_file, text_error
from shared.image import draw_boxes, norm_to_pixel


class BBox(BaseModel):
    bbox: Annotated[
        list[int],
        Field(description="[x1, y1, x2, y2] in normalized coordinates (0-1000)", min_length=4, max_length=4),
    ]
    label: Annotated[Optional[str], Field(description="Optional label text displayed above the box")] = None
    color: Annotated[
        Optional[str],
        Field(
            description=(
                "Optional box color as hex string (e.g. '#FF0000'). Cycles through a default palette if omitted."
            )
        ),
    ] = None


class DrawBboxArgs(BaseModel):
    image_path: Annotated[str, Field(description="Absolute path to the source image file")]
    bboxes: Annotated[list[BBox], Field(description="List of bounding boxes to draw")]
    output_path: Annotated[
        Optional[str],
        Field(
            description="Where to save the annotated image. Defaults to {stem}_annotated.{ext} next to the original."
        ),
    ] = None


TOOL: dict[str, Any] = {
    "name": "draw_bbox",
    "description": (
        "Draw bounding boxes on an image. "
        "Saves the annotated result to disk and returns a preview. "
        "Coordinates are normalized (0-1000), same as grounding output."
    ),
    "args": DrawBboxArgs,
}


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int] | None:
    h = hex_str.lstrip("#")
    if len(h) != 6:
        return None
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return None


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    image_path = arguments.get("image_path", "")
    if err := require_file(image_path):
        return err
    if err := require_dep("PIL", "pillow"):
        return err

    bboxes = arguments.get("bboxes")
    if not bboxes:
        return text_error("'bboxes' is required and must not be empty")

    from PIL import Image

    from freeglm_core.renderers import labeled_image

    img = Image.open(image_path)
    detections = [
        {
            "bbox_pixel": norm_to_pixel([int(v) for v in item["bbox"]], img.width, img.height),
            "label": item.get("label", ""),
            "color": _hex_to_rgb(item["color"]) if item.get("color") else None,
        }
        for item in bboxes
        if item.get("bbox") and len(item["bbox"]) == 4
    ]
    annotated = draw_boxes(img, detections)

    output_path = arguments.get("output_path") or default_output_path(image_path, "_annotated")
    from shared.image import save_image

    save_image(annotated, output_path)

    summary = (
        f"Drew {len(detections)} box(es) on: {image_path}\n"
        f"Saved to: {output_path} | {annotated.height}x{annotated.width} (HxW)"
    )
    return [{"type": "text", "text": summary}, *labeled_image("[Preview]", annotated, "normal")]
