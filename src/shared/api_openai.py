"""OpenAI-compatible chat client (shared): endpoint resolution + chat call with retry.

Used by the vision server's vision_chat / ocr / grounding. Targets any OpenAI-compatible endpoint
(DashScope's compatible-mode is only the default base_url; a Zhipu GLM backend — GLM-4.6V-Flash —
is the other built-in provider). The `openai` SDK is imported lazily so tool discovery stays cheap.
DashScope native-REST generation lives in `api_dashscope`.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from pathlib import Path
from typing import Any

from shared.env import DEFAULT_DASHSCOPE_BASE_URL, DEFAULT_ZHIPU_BASE_URL, get_env

log = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen3.7-plus"
# Zhipu GLM vision default — used when the Zhipu backend is selected (ZHIPU_API_KEY set, or
# `provider="zhipu"`) and ZHIPU_VISION_MODEL is unset.
DEFAULT_ZHIPU_VISION_MODEL = "glm-4.6v-flash"
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 1.0
# Request timeout (seconds) for a chat call — generous for long vision prompts, but bounded so a
# hung connection can't pin a tool call for an hour. Overridable via FREEGLM_CHAT_TIMEOUT.
DEFAULT_CHAT_TIMEOUT = 600

# Supported VL endpoint providers. `auto` picks DashScope unless only ZHIPU_API_KEY is set.
VL_PROVIDERS = ("auto", "dashscope", "zhipu")

# Per-model video-duration ceilings for SERVER-SIDE sampling (seconds), from Bailian/Model Studio docs
# (help.aliyun.com/zh/model-studio/vision, as of 2026-08). Prefix-matched against the model id; a model
# with no entry is treated as "unknown" → no cap (the endpoint still enforces its own limit). Only
# relevant on the OSS-upload path, where the whole video is sampled server-side.
_VL_VIDEO_MAX_SEC: dict[str, int] = {
    "qwen3.7-plus": 2 * 3600,  # flagship: up to 2 h / 2 GB
    "qwen-vl-max": 20 * 60,  # 2 s – 20 min, ≤ 1 GB
    "qwen3-vl": 20 * 60,
}


def vl_video_max_sec(model: str | None) -> int | None:
    """Server-side video-duration cap (seconds) for a VL ``model``, or None when unknown."""
    if not model:
        return None
    for prefix, cap in _VL_VIDEO_MAX_SEC.items():
        if model.startswith(prefix):
            return cap
    return None


def _chat_timeout() -> int:
    """FREEGLM_CHAT_TIMEOUT (seconds), read at call time; unset/bad values fall back to the default."""
    raw = get_env("FREEGLM_CHAT_TIMEOUT")
    try:
        return int(raw) if raw else DEFAULT_CHAT_TIMEOUT
    except ValueError:
        log.warning("FREEGLM_CHAT_TIMEOUT=%r is not a valid integer; using default %d", raw, DEFAULT_CHAT_TIMEOUT)
        return DEFAULT_CHAT_TIMEOUT


# HTTP statuses worth retrying for OpenAI-compatible endpoints.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def _provider_of(arguments: dict[str, Any], provider: str | None = None) -> str:
    """Normalize the VL provider: explicit argument > `provider` param > "auto"."""
    p = (arguments.get("provider") or provider or "auto").strip().lower()
    if p not in VL_PROVIDERS:
        log.warning("unknown VL provider %r; falling back to 'auto'", p)
        return "auto"
    return p


def _zhipu_selected() -> bool:
    """True when the Zhipu GLM backend is configured and DashScope is not — the `auto` rule that
    makes VL tools default to GLM-4.6V-Flash the moment ZHIPU_API_KEY is set."""
    return bool(get_env("ZHIPU_API_KEY")) and not get_env("DASHSCOPE_API_KEY")


def _is_zhipu_provider(provider: str | None = None) -> bool:
    """True when the effective backend is Zhipu GLM: explicit provider="zhipu", or "auto" with only
    ZHIPU_API_KEY set. Shared by model defaulting, endpoint resolution and media encoding so every
    layer agrees on which wire formats to emit."""
    p = _provider_of({}, provider)
    return p == "zhipu" or (p == "auto" and _zhipu_selected())


def default_vl_model(provider: str | None = None) -> str:
    """Default VL model for a provider: Zhipu GLM (ZHIPU_VISION_MODEL or GLM-4.6V-Flash) when the
    Zhipu backend is in play, else the DashScope default (Qwen). An explicit provider wins; the
    auto rule applies only when the provider is left at "auto"."""
    if _is_zhipu_provider(provider):
        return get_env("ZHIPU_VISION_MODEL") or DEFAULT_ZHIPU_VISION_MODEL
    return DEFAULT_MODEL


def resolve_openai_endpoint(arguments: dict[str, Any], provider: str | None = None) -> tuple[str, str]:
    """Resolve (base_url, api_key) for an OpenAI-compatible call.

    Provider precedence: explicit `provider` argument → configured environment → default; with `auto` the
    Zhipu GLM backend wins when ZHIPU_API_KEY is set and DASHSCOPE_API_KEY is not (so GLM-4.6V-Flash
    works with zero DashScope config). A programmatic explicit ``base_url`` is never paired with an
    environment key: callers must provide the key in the same trusted call, otherwise auth is
    ``"EMPTY"``. This defense prevents an untrusted URL from exfiltrating a configured credential.
    """
    p = _provider_of(arguments, provider)
    base_url = arguments.get("base_url")
    api_key = arguments.get("api_key")

    # Explicit endpoints are potentially untrusted. Never copy a user's environment credential to
    # one implicitly; an internal/programmatic caller that truly needs a custom endpoint must provide
    # its matching key in the same call. MCP schemas do not expose either field.
    if base_url:
        return base_url, api_key or "EMPTY"

    if p == "zhipu":
        return (
            get_env("ZHIPU_BASE_URL") or DEFAULT_ZHIPU_BASE_URL,
            api_key or get_env("ZHIPU_API_KEY") or "EMPTY",
        )
    if p == "dashscope":
        return (
            get_env("DASHSCOPE_BASE_URL") or DEFAULT_DASHSCOPE_BASE_URL,
            api_key or get_env("DASHSCOPE_API_KEY") or "EMPTY",
        )

    # auto: an explicit key may use the effective provider's standard/configured URL. Endpoint-only
    # overrides returned above deliberately get no environment credential.
    zhipu = _zhipu_selected()
    if api_key:
        return (
            (get_env("ZHIPU_BASE_URL") or DEFAULT_ZHIPU_BASE_URL)
            if zhipu
            else (get_env("DASHSCOPE_BASE_URL") or DEFAULT_DASHSCOPE_BASE_URL),
            api_key,
        )
    if zhipu:
        return get_env("ZHIPU_BASE_URL") or DEFAULT_ZHIPU_BASE_URL, get_env("ZHIPU_API_KEY") or "EMPTY"
    return (
        get_env("DASHSCOPE_BASE_URL") or DEFAULT_DASHSCOPE_BASE_URL,
        get_env("DASHSCOPE_API_KEY") or "EMPTY",
    )


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://", "data:"))


def encode_image_source(source: str) -> dict[str, Any]:
    """OpenAI-style image content part: a URL/data-URL passthrough, or a local file base64'd."""
    if is_url(source):
        return {"type": "image_url", "image_url": {"url": source}}
    path = Path(source)
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type is None or not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}


def _sample_local_video_frames(source: str, max_frames: int) -> tuple[list[str], float]:
    """Sample a LOCAL video into inline base64 JPEG data-URLs + the effective fps.

    Shared by the Qwen ``video`` part and the Zhipu image-part expansion so both wire formats come
    from one sampling path (probe → dynamic FPS → parallel keyframe-seek).
    """
    from shared.env import DEFAULT_FPS, TOKEN_SIZE, VIDEO_MIN_PIXELS
    from shared.image import smart_resize
    from shared.video import compute_dynamic_fps, extract_frames_by_seeking, get_video_info

    info = get_video_info(source)
    target_h, target_w = smart_resize(info["height"], info["width"], VIDEO_MIN_PIXELS, 1280 * TOKEN_SIZE**2)
    fps, nframes = compute_dynamic_fps(info["duration"], info["native_fps"], 4, max_frames, DEFAULT_FPS)
    frame_interval = info["duration"] / nframes if nframes > 0 else 0
    timestamps = [i * frame_interval for i in range(nframes)]
    frames = extract_frames_by_seeking(source, timestamps, target_h, target_w)
    return [f"data:image/jpeg;base64,{b64}" for _, b64 in frames], fps


def _sample_remote_video_frames(source: str, max_frames: int) -> list[str]:
    """Sample a remote video URL into inline base64 JPEG data-URLs.

    ffmpeg/ffprobe read http(s) URLs directly, so this is the same sampling path as a local file —
    probe the URL for size/duration, compute a dynamic FPS within ``max_frames``, and extract
    keyframe-seeked frames (no temp download).
    """
    urls, _ = _sample_local_video_frames(source, max_frames)
    return urls


def encode_video_source(
    source: str,
    max_frames: int = 128,
    *,
    allow_upload: bool = True,
    model: str | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """OpenAI-style video content part: a URL passthrough, an OSS upload, or a local file sampled
    into frames.

    Routing for a local video mirrors the Omni path (``shared.api_omni`` / the api ``omni/_common``) so
    both share ONE trigger — ``shared.oss.is_upload_configured()``: when OSS is configured the file is
    uploaded and handed over as a signed ``video_url`` (the endpoint samples it server-side, lifting the
    inline frame cap); otherwise it is sampled locally into inline frames. That upload path samples the
    whole video server-side, which caps duration per ``model`` — so a local file longer than the cap
    skips the upload and degrades to local frame sampling instead (sparse for very long clips, but it
    still returns a result). ``allow_upload=False`` suppresses the upload (used by ``dry_run`` so a
    preview never touches the network).

    Zhipu GLM (provider "zhipu") has no video modality: ``video_url``/``video`` parts are rejected
    with 4xx errors, so frames are always emitted as plain ``image_url`` parts and uploaded URLs
    degrade to frames too (checked against the caller's ``model`` cap).
    """
    if is_url(source):
        if _is_zhipu_provider(provider):
            # GLM can't ingest video_url; sample from the remote stream locally.
            return {"type": "video", "video": _sample_remote_video_frames(source, max_frames)}
        return {"type": "video_url", "video_url": {"url": source}}

    if allow_upload and not _is_zhipu_provider(provider):
        from shared import oss

        if oss.is_upload_configured():
            from shared.video import video_duration_exceeds

            if video_duration_exceeds(source, vl_video_max_sec(model)):
                log.warning(
                    "video %s exceeds the server-side duration limit for model %r; sampling frames "
                    "locally instead of uploading",
                    source,
                    model or DEFAULT_MODEL,
                )
            else:
                url = oss.upload_and_sign(source, key_prefix=get_env("OSS_VIDEO_CLIP_PREFIX", "tmp/video_clips"))
                return {"type": "video_url", "video_url": {"url": url}}

    urls, fps = _sample_local_video_frames(source, max_frames)
    if _is_zhipu_provider(provider):
        # GLM has no video modality — pass the sampled frames as plain images.
        return {"type": "video", "video": urls}
    return {"type": "video", "video": urls, "fps": round(fps, 2)}


def encode_video_as_images(
    source: str,
    max_frames: int = 128,
    *,
    allow_upload: bool = True,
    model: str | None = None,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Video → a list of OpenAI-style content parts, for building a message content array.

    On Zhipu GLM (no video modality, ``video``/``video_url`` parts are rejected) each sampled frame
    becomes its own ``image_url`` part — the only media format GLM accepts. On DashScope this is the
    single video part, i.e. ``[encode_video_source(...)]``.
    """
    if _is_zhipu_provider(provider):
        urls = (
            _sample_remote_video_frames(source, max_frames)
            if is_url(source)
            else _sample_local_video_frames(source, max_frames)[0]
        )
        return [{"type": "image_url", "image_url": {"url": u}} for u in urls]
    return [encode_video_source(source, max_frames, allow_upload=allow_upload, model=model, provider=provider)]


def call_openai_chat(
    *,
    base_url: str,
    api_key: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs: Any,
) -> Any:
    """Call OpenAI-compatible chat completions, retrying transient failures.

    Retries on the SDK's typed transient errors (rate limit, timeout,
    connection, 5xx) and on retryable HTTP status codes, rather than matching
    substrings of the error message.
    """
    # A missing key against a cloud endpoint just 401s with a terse message; give an actionable
    # error naming the env var for the endpoint being called — before pulling in the SDK, so the
    # guard works even when `openai` isn't installed. Local/self-hosted servers ignore auth, so
    # only guard the known DashScope and Zhipu endpoints.
    if api_key in ("", "EMPTY"):
        if "dashscope" in base_url:
            raise RuntimeError("no API key — set DASHSCOPE_API_KEY (or pass api_key)")
        if "bigmodel.cn" in base_url:
            raise RuntimeError("no API key — set ZHIPU_API_KEY (or pass api_key)")

    import openai
    from openai import OpenAI

    from shared.retry import retry_call

    retryable = (
        openai.RateLimitError,
        openai.APITimeoutError,
        openai.APIConnectionError,
        openai.InternalServerError,
    )

    def _is_transient(e: Exception) -> bool:
        return isinstance(e, retryable) or (
            isinstance(e, openai.APIStatusError) and getattr(e, "status_code", None) in _RETRYABLE_STATUS
        )

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=_chat_timeout())
    return retry_call(
        lambda: client.chat.completions.create(**kwargs),
        attempts=max_retries,
        base_backoff=DEFAULT_RETRY_BACKOFF,
        mode="linear",
        should_retry=_is_transient,
        on_exhausted="raise",
        log=log,
    )
