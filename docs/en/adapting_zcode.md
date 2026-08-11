# Adapting FreeGLM to ZCode (and any Claude-compatible harness)

FreeGLM ships as a **plugin marketplace** that ZCode (and Claude Code, Qoder, Codex, OpenClaw…)
can consume directly. This guide explains how the ZCode adaptation works, why it reuses the
Claude marketplace format, and how to replicate it for another harness — the same recipe the
upstream Qwen-MM-Plugins project uses for its per-harness support.

## What "adapting" means here

FreeGLM is **harness-agnostic**: every capability is a `skill/` (so the model knows the tools
exist) plus an optional MCP server package (`<import_name>/`). A harness "adaptation" is just the
thin registration layer that tells the harness where those live:

| Harness | Registration mechanism | Files that matter |
|---|---|---|
| ZCode | Claude-compatible plugin marketplace | `.zcode-plugin/marketplace.json` + per-cap `.zcode-plugin/plugin.json` |
| Claude Code | Claude plugin marketplace | `.claude-plugin/marketplace.json` + per-cap `.claude-plugin/plugin.json` |
| Codex | Codex plugin marketplace | `.codex-plugin/plugin.json` + `.mcp.json` |
| Qoder | Qoder plugin marketplace | `.qoder-plugin/plugin.json` + `.mcp.json` |
| OpenClaw / Qwen Code / Gemini | native verbs or marketplace | see `docs/en/installation.md` |

The MCP servers themselves are launched the same way everywhere — `uvx --from "freeglm[<cap>] @
git+https://github.com/yenns7/freeglm.git@main" freeglm-<cap>` — so adapting to a new harness is
never a code change, only a manifest.

## How the ZCode adaptation is wired

### 1. Root marketplace (`.zcode-plugin/marketplace.json`)

A Claude-schema marketplace. ZCode reads this to list FreeGLM's capabilities:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "freeglm",
  "description": "FreeGLM multimodal capabilities for ZCode — derived from Qwen-MM-Plugins with a Zhipu GLM-4.6V-Flash vision backend",
  "owner": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "plugins": [
    { "name": "freeglm-core", "description": "…", "author": { "name": "yenns7" }, "source": "./src/capabilities/core" },
    { "name": "freeglm-api",  "description": "…", "author": { "name": "yenns7" }, "source": "./src/capabilities/api" }
  ]
}
```

> The canonical marketplace lives at `.claude-plugin/marketplace.json`; `.zcode-plugin/marketplace.json`
> is generated from it (same schema). The `scripts/check_manifests.py` CI gate keeps every
> per-platform manifest in sync with `pyproject.toml`.

### 2. Per-capability manifest (`.zcode-plugin/plugin.json`)

Each capability folder carries one. For a server capability (`api` example):

```json
{
  "name": "freeglm-api",
  "version": "1.0.0",
  "description": "FreeGLM api — cloud APIs for understanding media: VL (vision_chat / ocr / grounding), Omni A/V, ASR, segmentation (SAM3), exposed as an MCP server.",
  "author": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "skills": "./skill",
  "mcpServers": {
    "freeglm-api": {
      "command": "uvx",
      "args": ["--from", "freeglm[api] @ git+https://github.com/yenns7/freeglm.git@main", "freeglm-api"]
    }
  }
}
```

For a skill-only capability (`edu-agent`), omit `mcpServers` — only `skills` is registered.

### 3. What ZCode installs

- **`skills`** — copied/registered so the model knows the toolset exists (the `SKILL.md` inside).
- **`mcpServers`** — a stdio MCP server, launched on demand by `uvx`. First launch resolves
  `freeglm[<cap>]` from the git URL and installs its Python extras into an isolated cache — no
  manual pip. `blender` / `freecad` additionally pass `FREEGLM_AUTOLAUNCH=1` in `env`.

## Replicating for another harness

1. **If the harness has a plugin marketplace** — copy the marketplace + per-cap manifests into its
   expected directory (`.codex-plugin/`, `.qoder-plugin/`, …) and add it to the root
   `marketplace.json` it reads. That's the entire adaptation.
2. **If it has native verbs but no marketplace** (Qwen Code, Gemini CLI) — `install.sh` automates
   those (`qwen extensions install …`, `gemini mcp add …`).
3. **If it needs a hand-edited config** (opencode, pi, QwenPaw) — register the MCP server + skill
   in the harness's own config; exact blocks are in `docs/en/installation.md`.

> Rule of thumb from the upstream project: **one marketplace, per-harness manifests, zero code
> changes** when adding a platform.

## ZCode quick-start prompt

Paste this into the ZCode agent after installing the `freeglm-*` capabilities to make it route
media through the tools (instead of any built-in OCR) and pick the right VL backend:

```text
You have FreeGLM MCP tools available. Rules:
1. To read / OCR / caption / ground any image or video, call the freeglm-* MCP tools
   (vision_chat / ocr / grounding). Never fall back to the harness's built-in image/OCR.
2. VL tools have two backends, auto-selected: Zhipu GLM-4.6V-Flash when only ZHIPU_API_KEY is
   set (model glm-4.6v-flash, endpoint open.bigmodel.cn); DashScope Qwen otherwise
   (model qwen3.7-plus). Force per call with provider="zhipu" / "dashscope".
3. Zhipu has no video modality — videos are sampled into image frames locally; keep
   video_max_frames ≈ video seconds (~1fps).
4. Omni A/V, ASR, segmentation, generation and search need DASHSCOPE_API_KEY / SERPER_API_KEY.
5. Use dry_run=true once per workflow to preview the request payload.
```

(Chinese version in `README.zh.md` → 给 Agent 的快速接入提示词.)
