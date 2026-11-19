# FreeGLM

A minimal vision MCP server that lets **text-only models "see" images** through a cloud vision model.

Every tool returns **text only** — images are processed by the cloud vision model, so the calling model only ever receives text. That makes the server usable with models that do not accept image input (such as `deepseek-v4-flash`) and with any model that does.

English · [中文](README.zh.md)

FreeGLM is a derived work of [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins) (Apache-2.0). It keeps the upstream multimodal Agent Skills and MCP servers and adds Zhipu GLM-4.6V-Flash as a free vision backend. See [UPSTREAM.md](UPSTREAM.md) for provenance and [NOTICE](NOTICE) for attribution.

## Tools

| Tool | Purpose |
|---|---|
| `vision_chat(images\|videos, text, ...)` | Ask questions about images or describe them (core tool); videos are sampled automatically |
| `ocr(images, ...)` | Text recognition, returned verbatim |
| `grounding(images, ...)` | Object localization: returns `[{"label","bbox_2d":[x1,y1,x2,y2]}]` with 0-1000 normalized coordinates |
| `media_info(path)` | ffprobe metadata for a video or audio file (duration, resolution, fps, codec, audio tracks) |
| `clear_memory()` | Clear the vision conversation memory for the current session |

## Built-in behaviour

1. **Exponential backoff** — 429, 5xx and network errors are retried after a wait. The primary model (4.6 Flash) is retried only once or twice before falling back, so a rate limit does not stall the whole call.
2. **Automatic fallback inside the free GLM family** — `glm-4.6v-flash` rate limited or timed out → `glm-4v-flash`. Both are free.
3. **Video frame sampling** — ffmpeg samples frames at a dynamic fps (12 frames by default), analyses them one by one and summarizes; temporary frames are cleaned up.
4. **Image cache keyed by content hash** — `~/.cache/vision-mcp/`, so the same file is not re-encoded.
5. **Lightweight conversation memory** — the last N rounds (4 by default) are kept in-process, so follow-up questions about the same image carry context. Disable per call with `memory=false`, clear with `clear_memory()`, or turn it off globally with `VISION_MCP_MEMORY=0`.

## Backends

| provider | Models | Endpoint | Key |
|---|---|---|---|
| `zhipu` | `glm-4.6v-flash` (primary) → `glm-4v-flash` (fallback), both free | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` |
| `qwen` | `qwen3.7-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `DASHSCOPE_API_KEY` |
| `auto` (default) | Stays on the free GLM fallback chain; does **not** switch to qwen | — | — |
| custom | Pass `base_url` + `api_key` + `model` to target any OpenAI-compatible endpoint, including Doubao Vision | — | — |

Keys are read from **environment variables first, then `~/.qwen-mm-plugins/config`, then an error**.

## Run

```bash
# As an MCP server over stdio, started by the agent:
python vision_server.py

# Dependencies: mcp and openai only
pip install mcp openai
```

Any MCP-capable agent can use it; register a stdio server pointing at
`python /path/to/vision_server.py`.

## Usage examples

> Look at this screenshot: `vision_chat(images=["/path/to/s.png"], text="What screen is this? List all the text")`
>
> Read the text in this image: `ocr(images=["/path/to/doc.png"])`
>
> Watch this video: `vision_chat(videos=["/path/to/clip.mp4"], text="What happens in the video?")`
>
> Locate objects: `grounding(images=["/path/to/photo.png"], text="Find every car")`
>
> Use Qwen instead: `vision_chat(images=[...], provider="qwen")`

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `VISION_MCP_MEMORY` | `1` | `0` disables conversation memory |
| `VISION_MCP_MEMORY_ROUNDS` | `4` | Number of rounds kept in memory |
| `VISION_MCP_MAX_FRAMES` | `12` | Maximum sampled frames per video (up to 64) |

## Notes

- The GLM fallback chain is **4.6 Flash (`glm-4.6v-flash`) → V4 Flash (`glm-4v-flash`)**, both free. Passing a `glm-*` model explicitly attaches the same chain; `qwen` and custom endpoints only try the model you name.
- `glm-4v-flash` caps `max_tokens` at 1024, so the server clamps the value when it falls back to that model.
- Images can be local paths (encoded automatically) or http(s) URLs.
- `dry_run=true` previews the request structure without sending it or spending quota.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
