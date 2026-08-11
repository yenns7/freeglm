# FreeGLM

**English** · [中文](README.zh.md)

Composable multimodal capabilities for agent harnesses.

FreeGLM is a set of installable Agent Skills and MCP servers for local media and file I/O, cloud media understanding, search, long-video memory, media generation and editing, and 3D/CAD workflows. It is derived from [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins) (Apache-2.0) and adds a Zhipu GLM-4.6V-Flash backend for `vision_chat`, `ocr`, and `grounding`; backend selection follows explicit configuration, not a price or latency comparison.

## Contents

- [🧩 Capabilities](#-capabilities)
- [🏗 Architecture](#-architecture)
- [🗺 Project map](docs/en/project-map.md)
- [🤖 Agent integration and routing](docs/en/agent-integration.md)
- [📦 Installation](#-installation)
- [🔧 Dependencies](#-dependencies)
- [🔑 Configuration](#-configuration)
- [🔌 Provider and API setup](docs/en/provider-setup.md)
- [🚀 Quick Start](#-quick-start)
- [🤖 Agent Quick-Start Prompt](#-agent-quick-start-prompt)
- [🧪 Development](#-development)
- [📄 License & Attribution](#-license--attribution)

## 🧩 Capabilities

Each capability is installed separately — a **skill** (so the model knows the toolset exists) plus an optional **MCP server** (the tools themselves).

We ship [**cookbooks**](cookbooks/) of these plugins in action — each capability's cookbook (linked in the table below) has its full tool listing, setup, and worked cases. Enjoy!

| Capability | What it does | Install name | Cookbook |
|---|---|---|---|
| **core** | Local I/O: read images/video, inspect media metadata, visualize supported document/data/code/3D/GIS/notebook formats, and crop, annotate, or save frames | `freeglm-core` | [link](cookbooks/core/usage.md) |
| **api** | External media-understanding services. `vision_chat` / `ocr` / `grounding` support DashScope Qwen or Zhipu GLM; Omni, dedicated ASR, and SAM3 segmentation have their own service requirements | `freeglm-api` | [link](cookbooks/api/usage.md) |
| **search** | Web search, page extraction, and reverse-image search via Serper. Reverse-searching a local image requires explicit consent because it is uploaded to a third-party public host | `freeglm-search` | [link](cookbooks/search/usage.md) |
| **video-memory** | Long-video memory: a hierarchical graph memory that powers QA over very long videos | `freeglm-video-memory` | [TBD](cookbooks/video-memory/usage.md) |
| **video-edit** | Video editing + generation: editing workflows + image / video / audio generation | `freeglm-video-edit` | [TBD](cookbooks/video-edit/usage.md) |
| **blender** | Blender 3D modeling: drive a **running** Blender via Python (thin client, 22 tools) — modeling / materials / lighting / rendering | `freeglm-blender` | [TBD](cookbooks/blender/usage.md) |
| **freecad** | FreeCAD parametric CAD: drive a **running** FreeCAD (thin client, 14 tools) — modeling, property edits, STEP/STL import/export, FEM analysis | `freeglm-freecad` | [TBD](cookbooks/freecad/usage.md) |
| **edu-agent** | Educational tutorial videos: turn a math/science problem or an image into a step-by-step Chinese explainer video / interactive page (**skill-only**, no MCP server) | `freeglm-edu-agent` | [TBD](cookbooks/edu-agent/usage.md) |

## 🏗 Architecture

![FreeGLM Architecture](docs/assets/architecture.svg)

See the [project map](docs/en/project-map.md) for directory ownership, capability boundaries, dependencies, and data-egress behavior. For tool selection, long-video routing, and multi-agent coordination, see [agent integration and routing](docs/en/agent-integration.md).

## 📦 Installation

A capability = a **skill** (so the model knows the tools exist) + an optional **MCP server** (the tools themselves, launched on demand by `uvx` — needs [uv](https://docs.astral.sh/uv/), no manual pip).

### Recommended: the guided installer

One script handles **install · configure · verify · uninstall** across every harness it supports (Claude Code · Codex · Qoder · OpenClaw · Qwen Code · Gemini CLI). It drives each harness's own native install under the hood — nothing reinvented — and writes a single shared config file (`~/.freeglm/config`) that GUI and terminal harnesses both read, so you set things up once:

```bash
curl -fsSL https://raw.githubusercontent.com/yenns7/freeglm/v1.0.2/install.sh | bash
```

**ZCode** has no plugin CLI on `PATH`. Open a workspace and use **Settings → Plugins → Create → Add marketplace URL → Install** for each required capability. The repository ships ZCode-ready manifests under `.zcode-plugin/`; see the [ZCode adaptation guide](docs/en/adapting_zcode.md) for the exact UI flow and manifest model.

Or run one action at a time — `bash install.sh install` / `configure` / `verify` / `uninstall` (what `configure` and `verify` do is detailed under [Configuration](#-configuration) and [Dependencies](#-dependencies)).

**Windows x64:** use WSL2 (Ubuntu recommended) and clone the repository inside your WSL
home directory (for example `~/code`), rather than under a mounted Windows drive such as
`/mnt/c`. Then run the same commands there. WSL2 is currently the only supported Windows
environment; native Windows has not yet been validated. See the concise
[Windows notes](docs/en/installation.md#windows-wsl2).

### By hand (per-harness)

Prefer your harness's own commands — or you're on opencode / pi / QwenPaw, which the installer doesn't cover? Register the skill + MCP yourself.

**Plugin-marketplace harnesses** (Claude Code · Qoder · Codex · OpenClaw · Qwen Code) — add the marketplace, then install a capability (replace `<cap>` with `core` / `api` / `search` / `video-memory` / `video-edit` / `blender` / `freecad`). Install `core` when the agent needs local file/media inspection, then add only the independent cloud, search, editing, or application capabilities the workflow actually needs:

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

Credentials must stay in the environment or the private `~/.freeglm/config` file. Never paste a key into chat, echo it to logs, commit it, or pass it as a tool argument. Agents may check whether a credential is configured, but must not read or display its value. External capabilities send queries or media to their configured providers; review the [data-egress table](docs/en/project-map.md#network-data-egress-and-credentials) before using private material.

For a safe GLM / DashScope / Serper walkthrough, layered validation, and troubleshooting, see
[provider and API setup](docs/en/provider-setup.md). For non-interactive/automation setup and the
environment-variable catalog, see [`docs/en/installation.md`](docs/en/installation.md).

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

Paste the concise policy below into an agent after installing the required capabilities. The full routing and multi-agent policy is in [agent integration and routing](docs/en/agent-integration.md).

```text
You have FreeGLM capabilities available. Route each task to the owning capability:

1. Use freeglm-core for local reading, metadata, visualization, cropping, annotation, and frames.
   Use freeglm-api only when an external model/service is needed for VQA, OCR, grounding, Omni,
   ASR, or segmentation. GLM is selected automatically only when ZHIPU_API_KEY is configured and
   DASHSCOPE_API_KEY is not; otherwise VL defaults to DashScope Qwen unless provider is explicit.
2. Use freeglm-video-memory for whole-video QA over videos of 30 minutes or more. For shorter video
   QA use core; for editing use freeglm-video-edit, adding video-memory only when long-source semantic
   navigation is useful. Re-read a narrow source window before asserting frame-level details.
3. Use freeglm-search only for external fact verification. Ask for explicit consent before a local
   image is uploaded for reverse search; do not upload private media without that consent.
4. Never request, print, echo, paste into chat, or pass credentials as tool parameters. Credentials
   come only from the process environment or the private ~/.freeglm/config file.
5. A lead agent owns the final answer and shared files. Delegate only independent, bounded work to
   parallel agents; give each agent non-overlapping outputs, then verify and integrate centrally.
```

## 🧪 Development

Development setup, contribution guidelines, and verification commands are in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Detailed guides: [local development](docs/en/local_development.md)
· [adding a capability](docs/en/how_to_add_new_capability.md) · [testing](docs/en/testing.md)
· [provider setup](docs/en/provider-setup.md) · [project map](docs/en/project-map.md)
· [agent integration](docs/en/agent-integration.md).

## 📄 License & Attribution

Apache-2.0 — see [`LICENSE`](LICENSE) and the [NOTICE](NOTICE) file.

This project is a **derived work** of [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins) by the Qwen team (Apache-2.0), imported from upstream commit [`8d6ea5a1f658260743307c52c2024ec87599fa48`](https://github.com/QwenLM/Qwen-MM-Plugins/commit/8d6ea5a1f658260743307c52c2024ec87599fa48). FreeGLM was published with standalone Git history and is **not** a GitHub formal fork, so GitHub's fork relationship must not be used as provenance. See [`UPSTREAM.md`](UPSTREAM.md) for the source baseline and local change scope.

The Blender and FreeCAD capabilities vendor third-party MIT-licensed code; see [`src/capabilities/blender/NOTICE.md`](src/capabilities/blender/NOTICE.md) and [`src/capabilities/freecad/NOTICE.md`](src/capabilities/freecad/NOTICE.md) for attribution.
