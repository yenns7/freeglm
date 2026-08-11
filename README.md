# FreeGLM

**English** · [中文](README.zh.md)

*“眼贴膜” — because it makes your agent see.* 😌

Native multimodal plugins for vision-language models — forked from [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins) (Apache-2.0), with a first-class **Zhipu GLM-4.6V-Flash** vision backend added alongside the original DashScope Qwen one. Make any agent harness multimodal-native, and let it pick the cheapest fast backend automatically.

## Contents

- [🧩 Capabilities](#-capabilities)
- [🏗 Architecture](#-architecture)
- [📦 Installation](#-installation)
- [🔧 Dependencies](#-dependencies)
- [🔑 Configuration](#-configuration)
- [🚀 Quick Start](#-quick-start)
- [🤖 Agent Quick-Start Prompt](#-agent-quick-start-prompt)
- [🧪 Development](#-development)
- [📄 License & Attribution](#-license--attribution)

## 🧩 Capabilities

Each capability is installed separately — a **skill** (so the model knows the toolset exists) plus an optional **MCP server** (the tools themselves).

We ship [**cookbooks**](cookbooks/) of these plugins in action — each capability's cookbook (linked in the table below) has its full tool listing, setup, and worked cases. Enjoy!

| Capability | What it does | Install name | Cookbook |
|---|---|---|---|
| **core** | Local I/O plugin: read images and video in dynamic resolution, and visualize any file (e.g. docs, 3D, and more) — plus some image tools (crop, annotate, extract frames) | `freeglm-core` | [link](cookbooks/core/usage.md) |
| **api** | Cloud APIs for understanding media, by model family. **VL** (vision chat, OCR, grounding) runs on **two backends**: DashScope Qwen (default, `qwen3.7-plus`) or **Zhipu GLM (`glm-4.6v-flash`)** — auto-selected when only `ZHIPU_API_KEY` is set, or per call via `provider="zhipu"`. Plus Omni A/V (timestamped captioning, ASR / multi-speaker diarization, temporal grounding, event counting), ASR and segmentation (SAM3) on DashScope | `freeglm-api` | [link](cookbooks/api/usage.md) |
| **search** | Web + reverse-image search to confirm facts: web search, page extraction, reverse image search; currently supports Serper | `freeglm-search` | [link](cookbooks/search/usage.md) |
| **video-memory** | Long-video memory: a hierarchical graph memory that powers QA over very long videos | `freeglm-video-memory` | [TBD](cookbooks/video-memory/usage.md) |
| **video-edit** | Video editing + generation: editing workflows + image / video / audio generation | `freeglm-video-edit` | [TBD](cookbooks/video-edit/usage.md) |
| **blender** | Blender 3D modeling: drive a **running** Blender via Python (thin client, 22 tools) — modeling / materials / lighting / rendering | `freeglm-blender` | [TBD](cookbooks/blender/usage.md) |
| **freecad** | FreeCAD parametric CAD: drive a **running** FreeCAD (thin client, 14 tools) — modeling, property edits, STEP/STL import/export, FEM analysis | `freeglm-freecad` | [TBD](cookbooks/freecad/usage.md) |
| **edu-agent** | Educational tutorial videos: turn a math/science problem or an image into a step-by-step Chinese explainer video / interactive page (**skill-only**, no MCP server) | `freeglm-edu-agent` | [TBD](cookbooks/edu-agent/usage.md) |

## 🏗 Architecture

![FreeGLM Architecture](docs/assets/architecture.svg)

## 📦 Installation

A capability = a **skill** (so the model knows the tools exist) + an optional **MCP server** (the tools themselves, launched on demand by `uvx` — needs [uv](https://docs.astral.sh/uv/), no manual pip).

### Recommended: the guided installer

One script handles **install · configure · verify · uninstall** across every harness it supports (Claude Code · Codex · Qoder · OpenClaw · Qwen Code · Gemini CLI). It drives each harness's own native install under the hood — nothing reinvented — and writes a single shared config file (`~/.freeglm/config`) that GUI and terminal harnesses both read, so you set things up once:

```bash
curl -fsSL https://raw.githubusercontent.com/yenns7/freeglm/main/install.sh | bash
```

**ZCode** has no CLI on `PATH`, so it's a one-shot manual step instead: add this repo as a plugin marketplace and install each capability from the ZCode UI (`marketplace add https://github.com/yenns7/freeglm.git` → `install freeglm-core@freeglm`). The repo ships zcode-ready manifests (`.zcode-plugin/`); full guide in [docs/en/adapting_zcode.md](docs/en/adapting_zcode.md).

Or run one action at a time — `bash install.sh install` / `configure` / `verify` / `uninstall` (what `configure` and `verify` do is detailed under [Configuration](#-configuration) and [Dependencies](#-dependencies)).

**Windows x64:** use WSL2 (Ubuntu recommended) and clone the repository inside your WSL
home directory (for example `~/code`), rather than under a mounted Windows drive such as
`/mnt/c`. Then run the same commands there. WSL2 is currently the only supported Windows
environment; native Windows has not yet been validated. See the concise
[Windows notes](docs/en/installation.md#windows-wsl2).

### By hand (per-harness)

Prefer your harness's own commands — or you're on opencode / pi / QwenPaw, which the installer doesn't cover? Register the skill + MCP yourself.

**Plugin-marketplace harnesses** (Claude Code · Qoder · Codex · OpenClaw · Qwen Code) — add the marketplace, then install a capability (replace `<cap>` with `core` / `api` / `search` / `video-memory` / `video-edit` / `blender` / `freecad`). Install `core` by default — it's the local-I/O base every other capability builds on — plus whichever others you need:

```bash
# Claude Code
claude   plugin  marketplace add https://github.com/yenns7/freeglm.git
claude   plugin  install       freeglm-<cap>@freeglm
# Qoder
qodercli plugins marketplace add https://github.com/yenns7/freeglm.git
qodercli plugins install       freeglm-<cap>@freeglm
# Codex
codex    plugin  marketplace add https://github.com/yenns7/freeglm.git
codex    plugin  add           freeglm-<cap>@freeglm
# OpenClaw
openclaw plugins install       freeglm-<cap> --marketplace https://github.com/yenns7/freeglm.git
# Qwen Code
qwen extensions install https://github.com/yenns7/freeglm.git:freeglm-<cap> --consent
```

`marketplace add` also accepts a local repo path; re-running is safe. On **codex**, `marketplace add` does **not** refresh an already-added marketplace, so run `codex plugin marketplace upgrade freeglm` before `plugin add` to pick up newly-published capabilities.

**Other harnesses** (Gemini CLI · opencode · pi · QwenPaw · **ZCode** · …) register the skill + MCP in their own config — exact per-harness blocks are in [`docs/en/installation.md`](docs/en/installation.md) and the [ZCode adaptation guide](docs/en/adapting_zcode.md). Easiest of all: **just ask the agent** — "install `freeglm-<cap>`".

## 🔧 Dependencies

`uvx` installs the Python dependencies for the chosen profile on first launch — no manual pip. The only things you install yourself are **system tools**: `ffmpeg` (video / audio), plus optional `libreoffice` / `blender` / `texlive` / `chromium` for `visualize`. Run `bash install.sh verify` to self-test what's installed — it confirms your API key and reports any missing system tools (fetching each capability's env and running `--check-system` under the hood). Full system-tool table, the edu-agent (skill-only) setup, and the blender/freecad thin-client notes: see [`docs/en/installation.md`](docs/en/installation.md).

## 🔑 Configuration

The API-based tools need a key — native image / video / document reading doesn't:

- `ZHIPU_API_KEY` — the **GLM-4.6V-Flash** vision backend for `vision_chat` / `ocr` / `grounding`. Set it alone and the VL tools route to Zhipu automatically (no DashScope key needed). Optional: `ZHIPU_BASE_URL`, `ZHIPU_VISION_MODEL`
- `DASHSCOPE_API_KEY` — `vision_chat` / `ocr` / `grounding` (Qwen backend) / `transcribe_audio` / Omni audio-video understanding / generation / video-memory build
- `SERPER_API_KEY` — `web_search` / `web_extractor` / `image_search`

Export them in your shell, or persist them to `~/.freeglm/config` (read whenever a var isn't already in the environment — so GUI-launched harnesses pick them up too). The guided installer's Configure step writes that file for you:

```bash
bash install.sh configure
```

For non-interactive/automation setup and the full environment-variable catalog, see [`docs/en/installation.md`](docs/en/installation.md).

## 🚀 Quick Start

Once a capability is installed, reference a file in your harness and just ask — the model picks the right tool automatically. Reading is **dynamic-resolution**: every image, video frame, and document page is auto-scaled to the VL model's patch grid, so a 4K screenshot's fine print and a tiny thumbnail both come in at the detail they need — no manual resizing.

```text
# core — read images / video / docs / 3D models (local, dynamic-resolution)
@dashboard-4k.png      Read every number in this dashboard.
@report.pdf            Summarize page 3.

# api — cloud VL + Omni APIs. VL tools route to GLM-4.6V-Flash when only ZHIPU_API_KEY is set,
# or to Qwen on DashScope; Omni / ASR / segmentation always use DashScope.
@receipt.jpg           OCR this and total the line items.                          # VL (GLM or Qwen)
@street.jpg            Draw a box around every car in the scene.                   # grounding
@meeting.mp4           Transcribe this with speaker labels and timestamps.         # omni
@sports-clip.mp4       Count every completed pass and list when each one occurs.   # omni
@song.mp3              Tag the genre, mood, instruments, key, and vocal profile.   # omni

# search — web + reverse-image search to confirm what's on screen
@place.jpg             Where was this photo taken?                 # image_search + web_search

# video-memory — QA over long videos; the first query auto-builds memory
@lecture-2h.mp4        What are the main points, with timestamps?

# video-edit — image / video / audio generation + editing workflows
                       Generate a 1024×1024 image of a red panda coding at night.
@/path/to/media        Help me edit this video down to about 3 minutes.

# blender — drive a running Blender to model / texture / light / render (thin client, 22 tools)
                       Model a low-poly wooden stool, add a warm key light, and render it.

# freecad — parametric CAD in a running FreeCAD (thin client, 14 tools; STEP/STL, FEM)
                       Model an M6 hex bolt 30 mm long and export it as STEP.

# edu-agent — turn a math/science problem into a step-by-step Chinese explainer video (skill-only)
@geometry-problem.png  Explain how to solve this as a narrated video.
```

See each capability's 🍳 [cookbook](cookbooks/) for every tool, setup, and a worked case.

## 🤖 Agent Quick-Start Prompt

FreeGLM is built for agents, and the fastest way to hook it up is to paste this into the agent (Claude Code / Codex / Qoder / any harness you've installed `freeglm-<cap>` on). It teaches the model the two VL backends and — importantly — that media understanding must go **through the MCP tools**, not through the harness's own built-in OCR/vision (so you get the model you configured, e.g. the free GLM-4.6V-Flash, instead of a local macOS OCR):

```text
You have FreeGLM MCP tools available. Rules:

1. MEDIA ALWAYS GOES THROUGH TOOLS. To read, OCR, caption, or ground any image/video,
   call the `freeglm-*` MCP tools (vision_chat / ocr / grounding). Never fall back to
   your harness's built-in image/OCR capabilities for these tasks.

2. VL backends (vision_chat / ocr / grounding) — two providers, selected automatically:
   - Zhipu GLM-4.6V-Flash: the default when only ZHIPU_API_KEY is set (zero DashScope config).
     Fast, free-tier, no thinking tokens. Model `glm-4.6v-flash`, endpoint open.bigmodel.cn.
   - DashScope Qwen: the default otherwise (DASHSCOPE_API_KEY). Model `qwen3.7-plus`.
   - Force a backend per call with provider="zhipu" or provider="dashscope".
   - Zhipu has NO video modality: videos are sampled into image frames locally — that's fine,
     keep video_max_frames within reason (frames = seconds for ~1fps).

3. Everything else (Omni A/V, ASR, segmentation, generation, search) needs DASHSCOPE_API_KEY /
   SERPER_API_KEY respectively — GLM does not cover those.

4. Prefer `dry_run=true` once per workflow to preview the request payload before calling.
```

## 🧪 Development

Development setup, contribution guidelines, and verification commands are in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Detailed guides: [local development](docs/en/local_development.md)
· [adding a capability](docs/en/how_to_add_new_capability.md) · [testing](docs/en/testing.md).

## 📄 License & Attribution

Apache-2.0 — see [`LICENSE`](LICENSE) and the [NOTICE](NOTICE) file.

This project is a **derived work** of [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins) by the Qwen team (Apache-2.0) — a fork that renames the project and adds a **Zhipu GLM-4.6V-Flash** vision backend (provider routing, video-to-frames degradation, `enable_thinking` isolation, config/verify wiring) on top of the upstream VL tools. Upstream changes can be tracked via the fork relationship on GitHub.

The Blender and FreeCAD capabilities vendor third-party MIT-licensed code; see [`src/capabilities/blender/NOTICE.md`](src/capabilities/blender/NOTICE.md) and [`src/capabilities/freecad/NOTICE.md`](src/capabilities/freecad/NOTICE.md) for attribution.
