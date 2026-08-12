#!/usr/bin/env python3
"""
vision-mcp — 极简视觉 MCP server。

让纯文本 agent（如 deepseek-v4-flash）通过工具调用云端视觉模型来"看图"。
所有工具都只返回文字：图片在云端处理，模型侧永远只收到文本，因此
对不支持图像输入的模型 100% 可用。

工具：
  vision_chat(images|videos, text, ...)   视觉问答 / 描述（核心，支持视频抽帧）
  ocr(images, ...)                         文字识别（vision_chat 的便捷封装）
  grounding(images, ...)                   目标定位：返回物体坐标（0-1000 归一化）
  media_info(path)                         视频/音频元数据探针（ffprobe）
  clear_memory()                           清空会话记忆

机制：
  指数退避重试（429/5xx 自动重试）、GLM 免费家族自动兜底、视频 ffmpeg 抽帧、
  图片 base64 内容哈希缓存、进程内轻量会话记忆（最近 N 轮，可开关）。

后端 (provider)：
  zhipu  GLM 免费家族     https://open.bigmodel.cn/api/paas/v4                       key: ZHIPU_API_KEY
         主选 4.6 Flash(glm-4.6v-flash)，限流/超时重试 1~2 次后立即切 V4 Flash(glm-4v-flash)
  qwen   Qwen3.7-Plus    https://dashscope.aliyuncs.com/compatible-mode/v1          key: DASHSCOPE_API_KEY
  auto   (默认) 固定走 zhipu GLM 免费家族兜底链，不切 qwen —— 整个流程只用免费 GLM 模型
  也可传 base_url / api_key / model 显式覆盖 —— 兼容任意 OpenAI 风格视觉端点
  （接 Doubao Vision 只需: provider 任意 + base_url + api_key + model）。

图片输入：本地文件路径（自动 base64 内联）或 http(s) 图片 URL。

运行：python vision_server.py   （stdio 传输，作为 MCP server 被拉起）
"""

import base64
import hashlib
import json
import logging
import mimetypes
import os
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vision-mcp")

# 日志走 stderr：MCP stdio 传输独占 stdout，打印到 stdout 会污染协议帧。
logger = logging.getLogger("vision-mcp")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

# ---- 内置后端 ----
# 配置文件回退：环境变量缺 key 时，读 ~/.qwen-mm-plugins/config（KEY=VALUE 每行）
CONFIG_FILE = Path.home() / ".qwen-mm-plugins" / "config"


def _env_or_config(name: str) -> Optional[str]:
    v = os.environ.get(name)
    if v:
        return v
    try:
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, val = line.partition("=")
                if k.strip() == name:
                    return val.strip()
    except OSError:
        pass
    return None


BACKENDS: dict[str, dict] = {
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPU_API_KEY",
        # 只用免费模型：4.6 Flash 主选（效果更好），但它高峰期 429 限流严重，
        # 故在主选上只重试 1~2 次就立刻切 V4 Flash（见 _call_model 的 retries）。
        "model": "glm-4.6v-flash",
        "fallback_models": ["glm-4v-flash"],
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "model": "qwen3.7-plus",
    },
}

# 各模型的 max_tokens 上限（超出会返回 400）。glm-4v-flash 上限只有 1024，
# 默认 2048 会让它直接失败，兜底到它时必须钳制。
MAX_TOKENS_LIMIT: dict[str, int] = {
    "glm-4v-flash": 1024,
}

# 重试次数：主选(glm-4.6v-flash)高峰期 429 限流频繁，重试 1~2 次就应
# 立即切 V4 Flash 兜底，避免指数退避拖长总耗时；兜底模型较稳，保留充足重试。
RETRY_MAIN = 2      # 主选模型重试次数
RETRY_FALLBACK = 4  # 兜底模型重试次数

# 兼容别名
ALIASES = {
    "dashscope": "qwen",
    "glm": "zhipu",
    "zhipuai": "zhipu",
}

# ---- 缓存 / 视频 / 会话记忆 全局 ----
CACHE_DIR = Path.home() / ".cache" / "vision-mcp"          # 图片 base64 内容哈希缓存
VIDEO_WORK_DIR = Path(tempfile.gettempdir()) / "vision-mcp-video"  # 抽帧临时目录
VIDEO_MAX_FRAMES = int(os.environ.get("VISION_MCP_MAX_FRAMES", "12"))

_MEM_LOCK = threading.Lock()                                # 会话记忆锁（进程=会话）
_conversations: dict[str, list[dict]] = {}                  # model -> 最近轮次 messages
MEMORY_ENABLED = os.environ.get("VISION_MCP_MEMORY", "1") != "0"
MEMORY_MAX_ROUNDS = int(os.environ.get("VISION_MCP_MEMORY_ROUNDS", "4"))


def _read_config(provider: str, base_url: Optional[str], api_key: Optional[str],
                 model: Optional[str], strict: bool = True) -> tuple[str, str, str]:
    """返回 (base_url, api_key, model)，参数 > 环境变量 > 内置默认。
    strict=False 时（dry_run 预览）缺 key 也放行，返回空 key。"""
    key = ALIASES.get(provider, provider)
    if key not in BACKENDS and provider not in ("auto", None):
        raise ValueError(
            f"未知 provider: {provider!r}。支持: auto / zhipu / qwen"
            f"（或传 base_url + api_key + model 自定义端点）"
        )
    if key in BACKENDS:
        base_url = base_url or BACKENDS[key]["base_url"]
        api_key = api_key or _env_or_config(BACKENDS[key]["api_key_env"])
        model = model or BACKENDS[key]["model"]
    else:  # auto / 自定义
        if key == "auto":
            # 默认只走 zhipu GLM 家族兜底链（不切 qwen）。
            # 仅当显式传了 base_url/api_key 时才按自定义端点处理。
            if base_url or api_key:
                return base_url, api_key or "", model or ""
            return _read_config("zhipu", None, api_key, model, strict)
        # 自定义端点
        api_key = api_key or ""
    if not api_key and strict:
        raise ValueError(
            f"缺少 API key：provider={key} 需要环境变量 {BACKENDS[key]['api_key_env']}"
            if key in BACKENDS else
            f"缺少 API key：自定义端点需要显式传 api_key"
        )
    return base_url, api_key or "", model


def _encode_images(images: list[str]) -> list[dict]:
    """本地路径 -> base64 data URL（按内容哈希缓存）；http(s) URL 原样透传。"""
    parts = []
    for src in images:
        if src.startswith(("http://", "https://", "data:")):
            parts.append({"type": "image_url", "image_url": {"url": src}})
            continue
        path = Path(src).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"图片不存在: {src}")
        mime, _ = mimetypes.guess_type(path.name)
        if mime is None or not mime.startswith("image/"):
            mime = "image/jpeg"
        # 内容哈希缓存：同一文件不重复读盘 + base64 编码
        raw = path.read_bytes()
        key = hashlib.sha256(raw).hexdigest()[:16]
        cache_file = CACHE_DIR / f"{key}.b64"
        b64 = None
        try:
            if cache_file.is_file():
                b64 = cache_file.read_text().strip()
        except OSError:
            pass
        if b64 is None:
            b64 = base64.b64encode(raw).decode("utf-8")
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(b64)
            except OSError:
                pass
        parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    return parts


def probe_media(path: str) -> dict:
    """ffprobe 探测视频/音频元数据（时长、分辨率、fps、编码、音轨）。"""
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(p)],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
        info = json.loads(out)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise RuntimeError(f"ffprobe 失败（需要系统安装 ffmpeg）: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"ffprobe 输出解析失败（文件可能损坏或不是媒体文件）: {e}") from e
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fmt = info.get("format", {})
    duration = float(fmt.get("duration") or video.get("duration") or 0)
    return {
        "path": str(p),
        "container": fmt.get("format_name", ""),
        "duration_s": round(duration, 2),
        "has_video": bool(video),
        "video_codec": video.get("codec_name", ""),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("r_frame_rate", ""),
        "has_audio": bool(audio),
        "audio_codec": audio.get("codec_name", ""),
    }


def _extract_frames(video_path: str, max_frames: int = VIDEO_MAX_FRAMES) -> list[str]:
    """ffmpeg 按动态 fps 抽帧，返回临时 jpg 文件路径列表（均匀覆盖整个时长）。"""
    p = Path(video_path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"视频不存在: {video_path}")
    info = probe_media(str(p))
    duration = info["duration_s"]
    if duration <= 0 or not info["has_video"]:
        raise ValueError("无法读取视频时长或没有视频流")
    max_frames = min(max(1, max_frames), 64)
    # 动态 fps：目标总帧数 / 时长，clamp 到 [0.1, 10]，保证长视频也均匀覆盖
    fps = max(0.1, min(10.0, max_frames / duration))
    # 用 时间戳+pid 避免同毫秒并发/残留目录冲突
    work = VIDEO_WORK_DIR / f"frames-{int(time.time() * 1000)}-{os.getpid()}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["ffmpeg", "-v", "quiet", "-i", str(p), "-vf", f"fps={fps}",
             str(work / "f_%04d.jpg")],
            capture_output=True, text=True, timeout=120, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(f"ffmpeg 抽帧失败: {e}") from e
    frames = sorted(work.glob("f_*.jpg"))
    if not frames:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError("未抽取到任何帧")
    # 帧数超过目标时均匀抽样（max_frames=1 时直接取首帧，避免除零）
    if len(frames) > max_frames and max_frames > 1:
        idxs = sorted(set(round(i * (len(frames) - 1) / (max_frames - 1)) for i in range(max_frames)))
        frames = [frames[i] for i in idxs]
    elif len(frames) > max_frames:
        frames = frames[:max_frames]
    paths = [str(f) for f in frames]
    # 抽帧临时目录只在本函数内使用（_chat 会马上读盘 base64），用完全部删掉，
    # 避免 /tmp 下积累 frames-* 目录。
    try:
        shutil.rmtree(work, ignore_errors=True)
    except OSError:
        pass
    return paths


def _call_with_retry(client, payload: dict, retries: int = 4, base: float = 1.5,
                     cap: float = 30.0) -> str:
    """指数退避 + 抖动重试：429 / 5xx / 网络错误 自动等待后重试。

    免费 GLM flash 模型 429 限流是常态，重试是稳定性的关键。空内容直接抛错
    （不重试同模型，交给外层 fallback 换模型）。
    """
    attempt = 0
    while True:
        try:
            resp = client.chat.completions.create(**payload, timeout=60)
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
            raise RuntimeError(f"模型 {payload['model']} 返回空内容")
        except Exception as e:  # noqa: BLE001
            status = getattr(e, "status_code", None)
            code = str(getattr(e, "code", "") or "")
            retryable = (
                status in (429, 500, 502, 503, 504)
                or "429" in str(e) or "1305" in code
                or "timeout" in str(e).lower() or "connect" in str(e).lower()
            )
            if not retryable or attempt >= retries:
                raise
            wait = min(cap, base * (2 ** attempt)) * (0.5 + random.random() * 0.5)
            logger.warning(
                "%s 请求失败(%s:%s)，第 %d/%d 次重试，%.1fs 后重试",
                payload["model"], status or "-", code or type(e).__name__,
                attempt + 1, retries, wait)
            time.sleep(wait)
            attempt += 1


def _call_model(provider: str, model: Optional[str], base_url: str, api_key: str,
                payload: dict) -> str:
    """候选链（保留 GLM 免费家族兜底语义）+ 指数退避重试。

    候选链规则（与之前一致）：
      zhipu / auto(未自定义端点)   → [指定或默认] + glm-4v-flash
      显式传的 GLM 模型 (glm-*)    → [该模型] + 上述兜底链
      qwen / 自定义端点 / 其他模型 → 只试 [model]
    """
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)

    key = ALIASES.get(provider, provider)
    glm_flow = key == "zhipu" or (key == "auto" and not base_url) or (
        key not in BACKENDS and (model or "").startswith("glm-"))
    if glm_flow:
        candidates = [model or BACKENDS["zhipu"]["model"]] + list(
            BACKENDS["zhipu"]["fallback_models"])
        candidates = list(dict.fromkeys(c for c in candidates if c))
    else:
        candidates = [model] if model else []
    if not candidates:
        raise ValueError("未指定 model（自定义端点需要显式传 model）")

    last_err: Optional[Exception] = None
    for idx, m in enumerate(candidates):
        p = dict(payload)
        p["model"] = m
        # glm-4v-flash 的 max_tokens 上限只有 1024，默认 2048 会让它直接 400
        p["max_tokens"] = min(payload.get("max_tokens", 2048),
                              MAX_TOKENS_LIMIT.get(m, payload.get("max_tokens", 2048)))
        # 主选(第一个)快速失败：只重试 1~2 次就切兜底，防止反复 429 + 指数退避
        # 把总耗时拖过工具超时上限；兜底模型保留充足重试防瞬时抖动。
        retries = RETRY_MAIN if idx == 0 else RETRY_FALLBACK
        try:
            return _call_with_retry(client, p, retries=retries)
        except Exception as e:  # noqa: BLE001 — 失败换下一个 fallback
            last_err = e
    raise last_err if last_err else RuntimeError("调用失败")


def _chat(provider: str, model: Optional[str], images: list[str], videos: list[str],
          text: str, base_url: Optional[str], api_key: Optional[str], max_tokens: int,
          temperature: Optional[float], dry_run: bool, memory: bool = True) -> str:
    base_url, api_key, model = _read_config(provider, base_url, api_key, model,
                                            strict=not dry_run)

    # 图片 + 视频抽帧统一成 image 内容块
    image_parts = _encode_images(images)
    video_frames: list[str] = []
    if videos:
        video_frames = _extract_frames(videos[0])
        image_parts.extend(_encode_images(video_frames))

    if dry_run:
        return json.dumps(
            {"base_url": base_url, "model": model,
             "n_parts": len(image_parts), "video_frames": len(video_frames),
             "request": "<preview: 图片已 base64 内联>"},
            ensure_ascii=False, indent=2)

    # ---- 轻量会话记忆：同一进程 = 同一会话，保留最近 N 轮问答 ----
    mem_key = model
    history: list[dict] = []
    if memory and MEMORY_ENABLED:
        with _MEM_LOCK:
            history = list(_conversations.get(mem_key, []))
    history = history[-2 * MEMORY_MAX_ROUNDS:]

    def _finalize(messages: list[dict]) -> str:
        """拼 payload、按需补 temperature、调用模型。"""
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
        if temperature is not None:
            payload["temperature"] = temperature
        return _call_model(provider, model, base_url, api_key, payload)

    # 多图（含视频帧）时逐图/逐帧分析后汇总，避免一次塞太多图进单请求
    if len(image_parts) > 1:
        n_img = len(image_parts) - len(video_frames)  # 列表前段是用户图片，后段是视频帧
        summaries = []
        for i, part in enumerate(image_parts):
            src_note = f"[画面 {i + 1}/{len(image_parts)}]" + (
                "（视频帧）" if i >= n_img else "")
            msgs = list(history)
            msgs.append({"role": "user", "content": [
                part, {"type": "text", "text": f"{src_note} {text}"}]})
            summaries.append(f"{src_note}\n{_finalize(msgs)}")
        result = "\n\n".join(summaries)
    else:
        content = list(image_parts) + [{"type": "text", "text": text}]
        msgs = list(history)
        msgs.append({"role": "user", "content": content})
        result = _finalize(msgs)

    # 记录本轮（文本摘要，不含图片 base64，避免内存膨胀）
    if memory and MEMORY_ENABLED:
        with _MEM_LOCK:
            conv = _conversations.setdefault(mem_key, [])
            conv.append({"role": "user",
                         "content": f"[图] {','.join(images + videos)} | {text}"[:300]})
            conv.append({"role": "assistant", "content": result[:1200]})
            _conversations[mem_key] = conv[-2 * MEMORY_MAX_ROUNDS:]
    return result


@mcp.tool()
def vision_chat(
    images: Optional[list[str]] = None,
    text: str = "请详细描述这张图片的内容。",
    provider: str = "auto",
    videos: Optional[list[str]] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: Optional[float] = None,
    memory: bool = True,
    dry_run: bool = False,
) -> str:
    """让云端视觉模型"看"图片（或视频抽帧）并返回文字回答（纯文本 agent 看图的核心工具）。

    Args:
        images: 图片的本地文件路径或 http(s) URL 列表。
        text: 对图片的提问 / 描述指令。
        provider: 视觉后端，'auto'(默认，固定走 GLM 免费家族) / 'zhipu'(GLM 免费兜底) / 'qwen'。
            zhipu 链路：4.6 Flash(glm-4.6v-flash) 限流/超时重试 1~2 次后立即
            切 V4 Flash(glm-4v-flash) 兜底，全程只用免费 GLM 模型，不会调用其他模型。
            显式传 GLM 模型(glm-*) 也会挂上这条兜底链。
        videos: 本地视频路径列表（最多 1 个）。自动 ffmpeg 抽帧（动态 fps，默认 ≤12 帧）
            后逐帧分析并汇总。想看视频前建议先调 media_info。
        model: 显式指定视觉模型名（覆盖 provider 默认）。
        base_url: 显式指定 OpenAI 兼容端点（覆盖 provider 默认，可接 Doubao 等）。
        api_key: 显式指定 API key（默认读环境变量 ZHIPU_API_KEY / DASHSCOPE_API_KEY）。
        max_tokens: 回答最大 token 数。
        temperature: 采样温度（None = 端点默认）。
        memory: 为 True 时保留会话级记忆（最近 N 轮问答），多轮追问同一张图时自动带上前文。
        dry_run: 为 True 时不真实请求，返回将发送的请求结构（调试用）。
    """
    images = images or []
    videos = videos or []
    if not images and not videos:
        raise ValueError("images 和 videos 至少提供其一")
    return _chat(provider, model, images, videos, text, base_url, api_key,
                 max_tokens, temperature, dry_run, memory)


@mcp.tool()
def ocr(
    images: Optional[list[str]] = None,
    provider: str = "auto",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 2048,
    dry_run: bool = False,
) -> str:
    """识别图片中的文字，原样返回（OCR）。

    Args:
        images: 图片的本地文件路径或 http(s) URL 列表。
        provider: 视觉后端，'auto'(默认) / 'zhipu' / 'qwen'。
        其余参数同 vision_chat。
    """
    if not images:
        raise ValueError("images 至少提供一张图片")
    return _chat(
        provider, model, images, [],
        "请识别图片中的所有文字，原样输出。如果是表格请保持结构；"
        "如果完全没有文字，请明确说明。不要添加额外解释。",
        base_url, api_key, max_tokens, None, dry_run, memory=False,
    )


@mcp.tool()
def grounding(
    images: Optional[list[str]] = None,
    text: str = "图中有什么物体？请全部列出并定位。",
    provider: str = "auto",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 2048,
    dry_run: bool = False,
) -> str:
    """目标定位：让视觉模型找出图中物体并返回归一化坐标（0-1000）。

    返回严格 JSON 数组，每项 {"label": 物体名, "bbox_2d": [x1,y1,x2,y2]}，
    坐标相对图片宽高归一化到 0-1000 —— 纯文本模型可直接换算像素、画框。
    注意：GLM/Qwen 免费模型对坐标精度为近似值，适合"大概在哪"。

    Args:
        images: 图片的本地文件路径或 http(s) URL 列表（1 张最稳）。
        text: 定位指令，建议点名要找的物体。
        provider / model / base_url / api_key / max_tokens / dry_run: 同 vision_chat。
    """
    images = images or []
    if not images:
        raise ValueError("images 至少提供一张图片")
    prompt = (
        f"{text}\n"
        "请只输出一个 JSON 数组，不要任何其他文字。格式：\n"
        '[{"label": "<物体名>", "bbox_2d": [x1, y1, x2, y2]}, ...]\n'
        "坐标是相对图片宽高的比例乘以 1000，范围 0-1000。找不到任何物体就输出 []。"
    )
    return _chat(provider, model, images, [], prompt, base_url, api_key,
                 max_tokens, None, dry_run, memory=False)


@mcp.tool()
def media_info(path: str) -> str:
    """探测视频/音频文件的元数据（时长、分辨率、fps、编码、是否有音轨等）。

    在看视频之前先调用它，判断视频能否抽帧、时长多少。需要系统已安装 ffmpeg。
    """
    info = probe_media(path)
    return json.dumps(info, ensure_ascii=False, indent=2)


@mcp.tool()
def clear_memory() -> str:
    """清空当前会话的视觉问答记忆（进程级，重启会话也会自然清空）。"""
    with _MEM_LOCK:
        _conversations.clear()
    return "已清空会话记忆"


if __name__ == "__main__":
    mcp.run(transport="stdio")
