"""MCP tool: exhaustive time-ordered event enumeration for counting questions."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from . import VideoPath


class EnumerateEventsArgs(BaseModel):
    video_path: VideoPath = None
    query: str = Field(
        description=(
            "Descriptive statement of the recurring event to enumerate (NOT a question). "
            "e.g. 'the player drinks wine from a gourd to restore health'."
        )
    )
    min_cosine: float = Field(
        default=0.5,
        description=(
            "Minimum cosine similarity to keep a match (default 0.5). "
            "Lower it (e.g. 0.4) if you suspect instances are missing; "
            "raise it (e.g. 0.6) if results contain many false positives."
        ),
    )
    max_results: int = Field(default=120, description="Maximum matches to return (cap 300).")
    node_types: Optional[list[str]] = Field(
        default=None,
        description="Node types to enumerate (default ['event']). Use ['entity'] to enumerate objects/people.",
    )


TOOL: dict[str, Any] = {
    "name": "enumerate_events",
    "description": (
        "Enumerate ALL matching event instances in time order — built for COUNTING and "
        "'how many times / list every occurrence' questions. "
        "Unlike search_nodes (top-k best matches), this returns every node above a similarity "
        "threshold, deduplicated and sorted by start time, in a compact format. "
        "Protocol for counting: "
        "1) Call this with a descriptive statement of the target event. "
        "2) Review the time-ordered list; merge adjacent entries that describe the same real occurrence. "
        "3) Verify borderline or ambiguous entries with read_video at their time ranges. "
        "4) If the expected count seems higher than returned matches, retry with lower min_cosine "
        "and also try alternative phrasings of the event. "
        "Never count from a single top-10 search — recurring events are spread across the whole video."
    ),
    "args": EnumerateEventsArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_video_memory.loader import get_toolkit

    args = dict(arguments or {})
    toolkit = get_toolkit(args.pop("video_path", None))
    result = toolkit.enumerate_events(
        query=args.get("query", ""),
        min_cosine=float(args.get("min_cosine", 0.5)),
        max_results=int(args.get("max_results", 120)),
        node_types=args.get("node_types"),
    )
    return [{"type": "text", "text": result}]
