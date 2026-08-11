"""MCP tool: text web search via the public Serper (Google Search) API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

SEARCH_PARAMS = {"gl": "us", "hl": "en", "location": "United States", "num": 10}


class WebSearchArgs(BaseModel):
    queries: list[str] = Field(description="List of search queries to execute.")


TOOL: dict[str, Any] = {
    "name": "web_search",
    "description": (
        "Search the internet for text information. Returns search results with titles, snippets, and URLs."
    ),
    "args": WebSearchArgs,
}


def _format_results(docs: list[dict[str, Any]], start_id: int = 1) -> tuple[str, int]:
    """Render Serper 'organic' docs; returns (text, next_id) with contiguous numbering."""
    lines = []
    i = start_id
    for doc in docs:
        url = doc.get("link", "")
        if not url:
            continue
        title = doc.get("title", "N/A")
        snippet = doc.get("snippet", "N/A")
        date = doc.get("date", "N/A")
        lines.append(f"[{i}] {url}\nTitle: {title}\nSnippet: {snippet}\nDate: {date}")
        i += 1
    text = "\n\n".join(lines) if lines else "No results found."
    return text, i


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_search.serper import post_serper, resolve_serper_key
    from shared.content import require_dep, text_error

    queries = arguments.get("queries", [])
    if not queries:
        return text_error("queries list is empty")
    if err := require_dep("requests"):
        return err

    api_key = resolve_serper_key(arguments)
    if not api_key:
        return text_error("no API key. Set SERPER_API_KEY in the environment or FreeGLM config.")

    all_results = []
    idx = 1
    for q in queries:
        data = post_serper("search", {"q": q, **SEARCH_PARAMS}, api_key, max_retries=10)
        docs = (data or {}).get("organic", [])
        text, idx = _format_results(docs, idx)
        all_results.append(f"## Query: {q}\n{text}" if len(queries) > 1 else text)

    tip = "\n\n---\nTip: Use `web_extractor` on the most relevant URL above to read the full page for detailed confirmation."
    return [{"type": "text", "text": "\n\n".join(all_results) + tip}]
