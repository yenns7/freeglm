"""Render source code files as markdown-fenced text blocks."""

from __future__ import annotations

import os
from typing import Any

_EXT_TO_LANG = {
    ".css": "css",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".xml": "xml",
    ".sql": "sql",
    ".md": "markdown",
    ".toml": "toml",
    ".ini": "ini",
    ".lua": "lua",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".dart": "dart",
    ".tex": "latex",
}

MAX_LINES = 500


def render(path: str, **opts: Any) -> list:
    ext = os.path.splitext(path)[1].lower()
    lang = _EXT_TO_LANG.get(ext, "")

    with open(path, "r", errors="replace") as f:
        lines = f.readlines()

    total_lines = len(lines)
    truncated = False
    if total_lines > MAX_LINES:
        lines = lines[:MAX_LINES]
        truncated = True

    code = "".join(lines)

    lang_label = lang.capitalize() if lang else ext.lstrip(".")
    summary = f"File: {path} | {lang_label} | {total_lines} lines"

    parts = [summary, f"```{lang}\n{code}\n```"]
    if truncated:
        parts.append(f"... ({total_lines - MAX_LINES} more lines truncated)")

    return [{"type": "text", "text": "\n\n".join(parts)}]
