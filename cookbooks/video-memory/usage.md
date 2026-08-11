# Cookbook — FreeGLM Video Memory

Long-video QA with `freeglm-video-memory`: the model builds a hierarchical graph memory
once, then answers content questions about a 30-minute-plus video without re-watching it.

---

## Tools

Usage is workflow-based: ask `@/path/to/video.mp4 <question>` in your harness. On the first query the
plugin builds a 4-level graph (Root → SuperEvent → MacroEvent → Subgraph) plus an embedding index
next to the video, then answers using these query tools (a drill-down pattern):

- `get_summary` — the video-level root summary (title, themes, key entities, tone)
- `get_super_events` — list the high-level narrative arcs (super events)
- `get_macro_events` — list macro events (optionally within a given super event)
- `get_subgraph` — drill into one macro event's detailed subgraph (entities / events / edges / on-screen text)
- `search_nodes` — semantic search over entity & event nodes by embedding similarity
- `enumerate_events` — enumerate ALL matching event instances in time order (built for counting / "how many times" questions)
- `search_ocr_text` — semantic search over on-screen text (OCR) nodes only
- `search_asr_text` — semantic search over the speech transcript (ASR) nodes
- `search_by_time` — find macro events covering a time range

---

## Install

```bash
claude plugin marketplace add https://github.com/yenns7/freeglm.git
claude plugin install freeglm-core@freeglm
claude plugin install freeglm-video-memory@freeglm
```

## Environment variables

### Required

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | DashScope API key. Used for VLM calls and embedding computation. Required for both building and querying memory. |

### Optional — Embedding / API

| Variable | Description | Default |
|----------|-------------|---------|
| `DASHSCOPE_BASE_URL` | Override the DashScope API base URL (for proxies or gateways); also used by the API-backed tools in `freeglm-core` such as `transcribe_audio`. | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

### Optional — Query

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPH_MEMORY_PATH` | Path to a specific `graph_memory.json`. **Takes precedence over the `video_path` parameter** when both are set; if unset, the server locates it via `video_path`. | Empty (looks up `<video_path>.memory/`) |
| `EMBEDDINGS_PATH` | Path to a specific `embeddings.npz`. | Empty (falls back to `<memory_dir>/embeddings.npz`) |
| `CUTOFF_SEC` | Time cutoff in seconds. Only macro events within this cutoff are loaded during queries. | None (no cutoff) |

### Optional — Build (OSS)

Only needed when building memory. They enable sending video clips to the VLM via signed OSS URLs
instead of inline base64 frames. If unset, the build falls back to base64 mode.

| Variable | Description | Default |
|----------|-------------|---------|
| `OSS_AK` | Alibaba Cloud OSS Access Key ID | Empty (OSS disabled) |
| `OSS_SK` | OSS Access Key Secret | Empty |
| `OSS_ENDPOINT` | OSS Endpoint URL | Empty |
| `OSS_BUCKET` | Target bucket for uploading video clips (takes precedence over `OSS_BUCKET_NAME`) | Empty |
| `OSS_VIDEO_CLIP_PREFIX` | Key prefix for uploaded video clips within the bucket | `tmp/video_clips` |
| `OSS_URL_EXPIRY` | Signed URL TTL in seconds | `7200` |

> Set these via env vars, `~/.freeglm/config`, or the guided installer **`bash install.sh`** (`bash install.sh verify` checks what's set).

---

## Cases

No case recorded yet. Add one in either style — see [core](../core/usage.md) for worked examples of both:

- **Trace** — a full session rendered to a self-contained HTML page, linked by URL.
- **Result** — the query plus a public link to the produced artifact (video / model / file) and/or a preview screenshot.
