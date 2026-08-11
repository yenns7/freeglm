"""MCP tool: semantic search over ASR (speech transcript) text."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from . import VideoPath


class SearchAsrTextArgs(BaseModel):
    video_path: VideoPath = None
    query: str = Field(description="Search text for spoken content, e.g. 'discussing weather', 'mentions recipe'.")
    top_k: int = Field(default=10, description="Number of results to return (default: 10).")


TOOL: dict[str, Any] = {
    "name": "search_asr_text",
    "description": (
        "Semantic search over ASR transcript text (speech, dialogue, narration). "
        "When to use: Question asks about spoken content, dialogue, narration, "
        "or any audio/verbal information in the video. "
        "Returns matching transcript segments with timestamps and macro event context."
    ),
    "args": SearchAsrTextArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_video_memory.loader import get_toolkit

    args = dict(arguments or {})
    toolkit = get_toolkit(args.pop("video_path", None))
    result = toolkit.search_asr_text(query=args.get("query", ""), top_k=int(args.get("top_k", 10)))
    return [{"type": "text", "text": result}]
