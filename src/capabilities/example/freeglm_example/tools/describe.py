"""Example tool (API call): ask an OpenAI-compatible chat model, optionally about an image.

Demonstrates the API-tool pattern (mirrors core's apis/ocr.py):
  1. resolve the endpoint + key via shared.env (through resolve_openai_endpoint — get_env under the hood),
  2. optionally attach a local image with require_file + encode_image_source,
  3. call the shared chat client and return the reply as text.

`dry_run=true` returns the request that WOULD be sent — no API key, no network — so the tool is
inspectable and testable offline.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from shared.api_openai import call_openai_chat, default_vl_model, encode_image_source, resolve_openai_endpoint
from shared.content import require_dep, require_file, text, text_error


class DescribeArgs(BaseModel):
    prompt: str = Field(description="What to ask the model (e.g. 'Describe this image', or any question).")
    image_path: str | None = Field(default=None, description="Optional local image file to attach to the prompt.")
    model: str | None = Field(default=None, description="Model id override (else the shared default).")
    dry_run: bool = Field(default=False, description="Return the request that WOULD be sent, without calling the API.")


TOOL: dict[str, Any] = {
    "name": "describe",
    "description": (
        "Ask an OpenAI-compatible chat model a question, optionally about a local image. "
        "Demonstrates an API-calling tool whose endpoint/key are resolved via shared.env. "
        "Set dry_run=true to see the request without a key or network call."
    ),
    "args": DescribeArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    prompt = arguments.get("prompt", "")
    image_path = arguments.get("image_path")
    model = arguments.get("model") or default_vl_model()

    # Endpoint + key come from user-controlled environment/config, never MCP tool arguments.
    base_url, api_key = resolve_openai_endpoint(arguments)

    # Build the OpenAI-style user message: optional image part, then the text prompt.
    parts: list[dict[str, Any]] = []
    if image_path:
        if err := require_file(image_path):
            return err
        parts.append(encode_image_source(image_path))
    parts.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": parts}]

    if arguments.get("dry_run"):
        preview = {"base_url": base_url, "model": model, "messages": messages, "has_api_key": bool(api_key)}
        return [text("DRY RUN — request that would be sent:\n" + json.dumps(preview, ensure_ascii=False, indent=2))]

    if err := require_dep("openai"):
        return err
    try:
        resp = call_openai_chat(base_url=base_url, api_key=api_key, model=model, messages=messages, max_tokens=1024)
        return [text(resp.choices[0].message.content or "")]
    except Exception as e:  # noqa: BLE001 — surface any API/SDK error as a tool message, not a crash
        return text_error(str(e))
