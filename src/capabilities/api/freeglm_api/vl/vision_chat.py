"""MCP tool: call vision-language model via OpenAI-compatible endpoint."""

from __future__ import annotations

import importlib.util
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from shared.content import text_error


class VisionChatArgs(BaseModel):
    model: Optional[str] = Field(
        default=None,
        description="Model name. Defaults to the provider's vision model (Qwen 'qwen3.7-plus' on DashScope, GLM 'glm-4.6v-flash' on Zhipu).",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Vision backend: 'auto' (default), 'dashscope', or 'zhipu' (GLM-4.6V-Flash). 'auto' picks DashScope, or Zhipu when only ZHIPU_API_KEY is set.",
    )
    text: str = Field(
        default="Describe the visual content.",
        description="Text prompt (default: 'Describe the visual content.')",
    )
    images: Optional[list[str]] = Field(default=None, description="Image URLs, data URLs, or local file paths")
    videos: Optional[list[str]] = Field(
        default=None,
        description="Video URLs or local file paths. Local files are auto-extracted into frames.",
    )
    max_tokens: int = Field(default=2048, description="Maximum tokens in response (default: 2048)")
    temperature: Optional[float] = Field(default=None, description="Sampling temperature")
    dry_run: bool = Field(default=False, description="If true, return the request payload without calling the endpoint")
    vl_high_resolution_images: bool = Field(
        default=False,
        description="Raise image token limit to 16384 (up to 16M pixels). Overrides max_pixels. DashScope/Qwen only.",
    )
    video_max_frames: int = Field(
        default=128,
        description="Max frames to extract from a local video. Default 128 (max 250); see the tool description for the 250-item and fps limits.",
    )


TOOL: dict[str, Any] = {
    "name": "vision_chat",
    "description": (
        "Chat with a vision-language model about images and videos. Backends: DashScope Qwen "
        "(default 'qwen3.7-plus') or Zhipu GLM ('glm-4.6v-flash' — used automatically when only "
        "ZHIPU_API_KEY is set, or via provider='zhipu'). "
        "Local videos are sampled into inline frames, so per request keep ≤ 250 items total "
        "(frames + images) and fps = frames / duration within [0.1, 10] — set video_max_frames to the "
        "video's length; for videos over ~40 min use read_video instead. "
        "Remote video URLs are handled server-side on DashScope; on Zhipu (no video modality) remote "
        "and local videos are both sampled into image frames locally. "
        "When OSS is configured (OSS_AK/OSS_SK/OSS_ENDPOINT/"
        "OSS_BUCKET) a local video is uploaded and sampled server-side instead, lifting the inline frame "
        "cap (still bounded by the model's server-side video-duration limit, e.g. 2 h for qwen3.7-plus). "
        "Use dry_run=true to preview the request payload without calling."
    ),
    "args": VisionChatArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    from shared.api_openai import (
        call_openai_chat,
        default_vl_model,
        encode_image_source,
        encode_video_as_images,
        resolve_openai_endpoint,
    )

    provider = arguments.get("provider")
    model = arguments.get("model") or default_vl_model(provider)
    text = arguments.get("text", "Describe the visual content.")
    images = arguments.get("images", [])
    videos = arguments.get("videos", [])
    base_url, api_key = resolve_openai_endpoint(arguments)
    max_tokens = arguments.get("max_tokens", 2048)
    temperature = arguments.get("temperature")
    dry_run = arguments.get("dry_run", False)
    vl_high_res = arguments.get("vl_high_resolution_images", False)
    # Clamp to the documented 1..250 range (see the tool description).
    video_max_frames = min(max(arguments.get("video_max_frames", 128), 1), 250)

    try:
        content: list[dict[str, Any]] = []
        for img in images:
            content.append(encode_image_source(img))
        for vid in videos:
            # dry_run must not hit the network, so suppress the OSS upload and preview the local path.
            # On the Zhipu GLM backend each video expands into per-frame image parts.
            content.extend(
                encode_video_as_images(vid, video_max_frames, allow_upload=not dry_run, model=model, provider=provider)
            )
        content.append({"type": "text", "text": text})
        messages = [{"role": "user", "content": content}]

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        if vl_high_res:
            kwargs["extra_body"] = {"vl_high_resolution_images": True}

        if dry_run:
            payload: dict[str, Any] = {"base_url": base_url, "request": kwargs}
            from shared import oss

            local_videos = [v for v in videos if not v.startswith(("http://", "https://", "data:"))]
            if local_videos and oss.is_upload_configured():
                payload["note"] = (
                    "OSS is configured — on a real call each local video is uploaded and passed as a "
                    "signed video_url (sampled server-side, no frame cap), NOT the inline frames "
                    "previewed here."
                )
            for msg in payload["request"]["messages"]:
                for item in msg.get("content", []):
                    if item.get("type") == "video" and "video" in item:
                        item["video"] = [
                            f"<base64 frame {i + 1}/{len(item['video'])}>" for i in range(len(item["video"]))
                        ]
                    if item.get("type") == "image_url":
                        url = item.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            item["image_url"]["url"] = f"<base64 image, {len(url)} chars>"
            return [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}]

        if importlib.util.find_spec("openai") is None:
            return text_error("missing dependency. Install with: pip install openai")

        response = call_openai_chat(base_url=base_url, api_key=api_key, **kwargs)
        result = response.model_dump()
        return [{"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}]

    except Exception as e:
        return text_error(f"{e}")
