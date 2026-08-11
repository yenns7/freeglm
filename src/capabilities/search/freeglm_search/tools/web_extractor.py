"""MCP tool: web page content extraction via the public Serper scrape API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

CONTENT_LIMIT = 8000  # chars of scraped page kept per URL


class WebExtractorArgs(BaseModel):
    urls: list[str] = Field(description="URLs to crawl and extract content from.", min_length=1)
    goal: str = Field(description="What information to extract or focus on.")
    api_key: Optional[str] = Field(default=None, description="Serper API key (defaults to SERPER_API_KEY).")


TOOL: dict[str, Any] = {
    "name": "web_extractor",
    "description": (
        "Crawl and extract content from web pages, with optional summarization. "
        "Returns the extracted text or a summary focused on the specified goal."
    ),
    "args": WebExtractorArgs,
}


def _scrape_page(url: str, api_key: str) -> str:
    """Scrape a URL via Serper; returns its markdown/text, or an error/empty note."""
    from freeglm_search.serper import post_serper

    data = post_serper("scrape", {"url": url, "includeMarkdown": True}, api_key, max_retries=3)
    if data is None:
        return f"Error scraping {url}"
    return data.get("markdown") or data.get("text") or "No content extracted."


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from freeglm_search.serper import resolve_serper_key
    from shared.content import require_dep, text_error

    urls = arguments.get("urls", [])
    goal = arguments.get("goal", "")
    if not urls:
        return text_error("urls list is empty")
    if err := require_dep("requests"):
        return err

    api_key = resolve_serper_key(arguments)
    if not api_key:
        return text_error("no API key. Set SERPER_API_KEY or pass api_key.")

    results = []
    for url in urls:
        content = _scrape_page(url, api_key)
        if content and not content.startswith("Error"):
            truncated = content[:CONTENT_LIMIT]
            results.append(f"## {url}\n(Goal: {goal})\n\n{truncated}" if goal else f"## {url}\n\n{truncated}")
        else:
            results.append(f"## {url}\n{content}")

    text = "\n\n".join(results) if results else "Could not extract content."
    return [{"type": "text", "text": text}]
