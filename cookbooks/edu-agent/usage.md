# Cookbook — FreeGLM Edu Agent

`freeglm-edu-agent` turns a math/science problem — typed or as an image — into a step-by-step
Chinese explainer **video** or an interactive page. It is **skill-only**: there is no MCP server, so
the model scaffolds, renders, and voices the video itself.

---

## How it works (no MCP tools)

A pure Agent Skill. Given a problem, the model:

1. **Solves & scripts** — works the problem into ordered explanation steps.
2. **Renders** — scaffolds an animated scene per step via `npx hyperframes`.
3. **Voices** — narrates each step with Qwen-TTS.
4. **Stitches** — muxes frames + audio into a final MP4 (or an interactive HTML page) with ffmpeg.

Because there is no MCP server, `uvx` installs nothing for it — its runtime dependencies are prepared
manually.

---

## Install

```bash
claude plugin marketplace add https://github.com/yenns7/freeglm.git
claude plugin install freeglm-core@freeglm
claude plugin install freeglm-edu-agent@freeglm
```

## Prerequisites

- **Node.js ≥ 18** + the `hyperframes` CLI (via `npx`)
- Python: `dashscope`, `soundfile`, `numpy`, `requests`
- `ffmpeg` on PATH
- `DASHSCOPE_API_KEY` (for Qwen-TTS narration)

📖 Full dependency table, network boundary, and prerequisites: [installation.md](../../docs/en/installation.md).

> Set these via env vars, `~/.freeglm/config`, or the guided installer **`bash install.sh`** (`bash install.sh verify` checks what's set).

---

## Cases

No case recorded yet. Add one in either style — see [core](../core/usage.md) for worked examples of both:

- **Trace** — a full session rendered to a self-contained HTML page, linked by URL.
- **Result** — the query plus a public link to the produced artifact (video / model / file) and/or a preview screenshot.
