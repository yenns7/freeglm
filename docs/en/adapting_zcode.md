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

The MCP servers themselves are launched from the same immutable release everywhere — `uvx --from
"freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1" freeglm-<cap>` — so adapting to
a new harness is never a server-code change, only a registration manifest.

## How the ZCode adaptation is wired

### 1. Root marketplace (`.zcode-plugin/marketplace.json`)

A Claude-schema marketplace. ZCode reads this to list FreeGLM's capabilities:

```json
{
  "name": "freeglm",
  "owner": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "metadata": {
    "description": "FreeGLM multimodal Agent Skills + MCP servers for local media I/O, cloud understanding, search, creation, and 3D/CAD workflows",
    "version": "1.0.1"
  },
  "plugins": [
    { "name": "freeglm-core", "source": "./src/capabilities/core", "description": "…" },
    { "name": "freeglm-api",  "source": "./src/capabilities/api",  "description": "…" }
  ]
}
```

> The canonical marketplace lives at `.claude-plugin/marketplace.json`; the checked-in
> `.zcode-plugin/marketplace.json` mirrors its metadata and plugin entries. The
> `scripts/check_manifests.py` CI gate checks the mirror, every platform manifest, the immutable
> release ref, and `pyproject.toml` together.

### 2. Per-capability manifest (`.zcode-plugin/plugin.json`)

Each capability folder carries one. For a server capability (`api` example):

```json
{
  "name": "freeglm-api",
  "version": "1.0.1",
  "description": "FreeGLM API — cloud media understanding by model family: VL vision chat, OCR, and grounding on DashScope Qwen or Zhipu GLM-4.6V-Flash; Omni A/V, ASR, and segmentation on DashScope.",
  "author": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "skills": "./skill",
  "mcpServers": {
    "freeglm-api": {
      "command": "uvx",
      "args": ["--from", "freeglm[api] @ git+https://github.com/yenns7/freeglm.git@v1.0.1", "freeglm-api"]
    }
  }
}
```

For a skill-only capability (`edu-agent`), omit `mcpServers` — only `skills` is registered.

### 3. What ZCode installs

- **`skills`** — copied/registered so the model knows the toolset exists (the `SKILL.md` inside).
- **`mcpServers`** — a stdio MCP server, launched on demand by `uvx`. First launch resolves
  `freeglm[<cap>]` from the `v1.0.1` git tag and installs its Python extras into an isolated cache — no
  manual pip. `blender` / `freecad` additionally pass `FREEGLM_AUTOLAUNCH=1` in `env`.

### 4. Install in ZCode

ZCode has no plugin CLI on `PATH`. Open a workspace, then go to **Settings → Plugins → Create →
Add marketplace**, enter `https://github.com/yenns7/freeglm.git`, find the desired
`freeglm-<cap>` entry under Personal, and click **Install**. Refresh the marketplace from the
marketplace source panel after a new release is published.

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

## Agent routing policy

After installation, use the shared [Agent integration and routing policy](agent-integration.md)
instead of maintaining a ZCode-specific prompt. It requires live Skill/MCP inventory checks,
routes tasks to the owning capability, forbids passing credentials through prompts or tool
arguments, covers private-media consent, and uses preview/`dry_run` only when the live tool schema
advertises it and a concrete diagnostic need exists.
