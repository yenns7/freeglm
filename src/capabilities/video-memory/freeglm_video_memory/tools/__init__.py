"""Graph-memory retrieval tools (one TOOL + handle per module)."""

from typing import Annotated, Optional

from pydantic import Field

# Shared field type: every tool accepts an optional video_path to locate the memory.
VideoPath = Annotated[
    Optional[str],
    Field(description="Path to the video file. Memory auto-loaded from <video_path>.memory/"),
]
