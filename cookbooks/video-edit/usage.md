# Cookbook — FreeGLM Video Edit

`freeglm-video-edit` pairs a video-editing skill with DashScope **generation** tools —
image, TTS, and text/image→video. The model can generate assets and stitch them into an edit.

---

## Tools

**Generation tools (DashScope)**
- `qwen_image` — image generation, editing, and translation (Qwen-Image)
- `qwen_tts` — text-to-speech (Qwen3-TTS-Flash)
- `wan_s2v` — digital-human lip-sync video (Wan2.2-S2V)
- `wan_t2v` — text-to-video (Wan, wan2.7 series)
- `happyhorse` — video generation and editing (HappyHorse)

**Editing skill** — the editing side is driven by the skill under the capability's
[`skill/`](../../src/capabilities/video-edit/skill/): `workflows/` (end-to-end recipes), `engines/`
(rendering-engine selection matrix), `mcps/` (external-service catalog), plus `craft/`, `looks/`, and
`review/` (technique, style, and QA references).

---

## Install

```bash
claude plugin marketplace add https://github.com/yenns7/freeglm.git
claude plugin install freeglm-core@freeglm
claude plugin install freeglm-video-edit@freeglm
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `DASHSCOPE_API_KEY` | Required — all generation tools (`qwen_image`, `qwen_tts`, `wan_s2v`, `wan_t2v`, `happyhorse`) call DashScope. |
| `DASHSCOPE_BASE_URL` | Optional — override the DashScope base URL (proxies/gateways). |

> Set these via env vars, `~/.freeglm/config`, or the guided installer **`bash install.sh`** (`bash install.sh verify` checks what's set).

---

## Cases

No case recorded yet. Add one in either style — see [core](../core/usage.md) for worked examples of both:

- **Trace** — a full session rendered to a self-contained HTML page, linked by URL.
- **Result** — the query plus a public link to the produced artifact (video / model / file) and/or a preview screenshot.
