"""MCP tool: OCR text extraction via vision-language model."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class OcrArgs(BaseModel):
    image_path: str = Field(description="Absolute path to the image file")
    prompt: Optional[str] = Field(
        default=None,
        description=(
            "Custom OCR instruction. Default extracts all visible text. "
            "Override to focus on specific regions or languages."
        ),
    )
    model: Optional[str] = Field(
        default=None,
        description="Model name. Defaults to the provider's vision model (Qwen 'qwen3.7-plus' on DashScope, GLM 'glm-4.6v-flash' on Zhipu).",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Vision backend: 'auto' (default), 'dashscope', or 'zhipu' (GLM-4.6V-Flash). 'auto' picks DashScope, or Zhipu when only ZHIPU_API_KEY is set.",
    )


TOOL: dict[str, Any] = {
    "name": "ocr",
    "description": (
        "Extract text from an image using a vision-language model. "
        "Backends: DashScope Qwen (default 'qwen3.7-plus') or Zhipu GLM ('glm-4.6v-flash' — used "
        "automatically when only ZHIPU_API_KEY is set, or via provider='zhipu'). "
        "Supports printed text, handwriting, documents, signs, and more. "
        "Returns the recognized text content."
    ),
    "args": OcrArgs,
}

DEFAULT_PROMPT = "请对这张图片进行OCR文字识别，提取图片中所有可见的文字内容，保持原始排版格式。"


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from shared.api_openai import call_openai_chat, default_vl_model, resolve_openai_endpoint
    from shared.content import require_dep, require_file

    image_path = arguments.get("image_path", "")
    prompt = arguments.get("prompt") or DEFAULT_PROMPT
    provider = arguments.get("provider")
    model = arguments.get("model") or default_vl_model(provider)
    base_url, api_key = resolve_openai_endpoint(arguments)

    if err := require_file(image_path):
        return err
    if err := require_dep("openai"):
        return err

    from shared.api_openai import encode_image_source

    messages = [
        {
            "role": "user",
            "content": [
                encode_image_source(image_path),
                {"type": "text", "text": prompt},
            ],
        }
    ]

    try:
        response = call_openai_chat(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            max_tokens=4096,
        )
    except Exception as e:
        from shared.content import text_error

        return text_error(f"{e}")
    return [{"type": "text", "text": response.choices[0].message.content or ""}]
