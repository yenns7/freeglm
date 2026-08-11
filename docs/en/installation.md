# Installation (detailed)

The fast paths — plugin marketplace and the guided installer — are in the [README](../../README.md#-installation). This page covers **non-plugin harnesses** (manual skill + MCP install), the resulting tool-name prefixes, the full dependency reference, and the repository layout.

## Windows (WSL2)

Windows x64 users should install WSL2 with Ubuntu and clone the repository inside the WSL
home directory (for example `~/code`), rather than under a mounted Windows drive such as
`/mnt/c`. Then follow the same installation commands as Linux/macOS. From an elevated
PowerShell terminal, WSL2 can be installed with:

```powershell
wsl --install -d Ubuntu
```

When using Codex on Windows, set the agent environment to WSL2, restart Codex, and install
and use the plugin inside that same WSL environment. WSL2 is currently the only supported
Windows environment; native Windows has not yet been validated.

## Non-marketplace harnesses: register skill + MCP directly

Harnesses without a plugin marketplace register the **skill** and **MCP server** in their own config. **Qwen Code** and **Gemini CLI** are automated by the [guided installer](../../README.md#-installation) (`bash install.sh` → pick the harness); the rest (opencode, pi, QwenPaw, …) are manual — per-harness steps below. For anything else, the easiest path is to **ask the agent to do it for you** ("install `freeglm-<cap>`").

For installer automation, the public overrides are `FREEGLM_REPO`, `FREEGLM_REF`,
`FREEGLM_NO_TUI`, and `FREEGLM_SPIN_TIMEOUT`; the older `QMP_*` names remain compatibility
aliases. The default remote release is the immutable `v1.0.1` tag.

Each capability is `freeglm-<cap>` with uvx extras `[<cap>]`; in every block below, replace `<cap>` with a capability name (`core` / `api` / `search` / `video-memory` / `video-edit` / `blender` / `freecad`).

Claude Code can also install this way — the only difference from the marketplace path is the tool name: marketplace installs carry a plugin prefix + a server key (the capability's own name, e.g. `freeglm-<cap>`), whereas a manual `mcp add` uses the server name you choose. Taking a capability's `read_image` as an example:

- Marketplace: `mcp__plugin_freeglm-<cap>_freeglm-<cap>__read_image`
- Manual: `mcp__freeglm-<cap>__read_image`

### skill link + mcp add (Claude Code and similar)

```bash
# 1) skill
ln -s "$(pwd)/src/capabilities/<cap>/skill" ~/.claude/skills/freeglm-<cap>
# 2) MCP (for local code, replace --from with "$(pwd)[<cap>]")
claude mcp add freeglm-<cap> -- \
  uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1" freeglm-<cap>
```

To switch capabilities, replace the skill path, the `[<cap>]` profile, and the entry name `freeglm-<cap>` all together with those of the target capability.

### opencode

`npm i -g opencode-ai`, then register the MCP server under `mcp` in `~/.config/opencode/opencode.json` (or a project `opencode.json`) and drop the skill in `~/.config/opencode/skills/`:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "freeglm-<cap>": {
      "type": "local",
      "command": ["uvx", "--from", "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1", "freeglm-<cap>"],
      "enabled": true
    }
  }
}
```

Do not add API-key placeholders to this block. The child process inherits variables that are
actually present and FreeGLM independently reads its private `~/.freeglm/config`; an empty
interpolation can otherwise mask a configured value.

```bash
cp -r src/capabilities/<cap>/skill ~/.config/opencode/skills/freeglm-<cap>   # opencode also reads ~/.claude/skills/
```

Headless: `opencode run "…"`. (A custom OpenAI-compatible provider must mark the model image-capable with `modalities`, or opencode drops returned images.)

### Qwen Code

`npm i -g @qwen-code/qwen-code@latest`. Install a capability as a **native extension** (bundles skill + MCP + context) in one command, from the Claude marketplace over git:

```bash
qwen extensions install https://github.com/yenns7/freeglm.git:freeglm-<cap> --consent
```

Or register just the MCP server (then copy the skill into `~/.qwen/skills/freeglm-<cap>`):

```bash
qwen mcp add freeglm-<cap> --scope user --trust --timeout 600000 \
  uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1" freeglm-<cap>
```

Headless: `qwen -p "…" --yolo -o text`. Uninstall: `qwen extensions uninstall freeglm-<cap>`.

### Gemini CLI

`npm i -g @google/gemini-cli`. Register the MCP server + install the skill:

```bash
gemini mcp add -s user freeglm-<cap> \
  uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1" freeglm-<cap>
gemini skills install https://github.com/yenns7/freeglm.git --path src/capabilities/<cap>/skill --consent
```

The capability directories are not standalone Gemini extensions (they intentionally have no `gemini-extension.json`), so use the two native commands above for both remote and local installations instead of `gemini extensions link`. MCP loads only in **trusted** folders (trust it when prompted). Headless: `gemini -p "…" -y`. Uninstall: `gemini mcp remove -s user freeglm-<cap>` + `gemini skills uninstall freeglm-<cap>`.

> Gemini CLI only talks to the **Google Gemini API** — no external / OpenAI-compatible model providers.

### pi (earendil-works)

`npm i -g @earendil-works/pi-coding-agent`. pi has **native skills** but **no built-in MCP** (by design) — MCP tools come via the community `pi-mcp-adapter` extension:

```bash
cp -r src/capabilities/<cap>/skill ~/.pi/agent/skills/freeglm-<cap>   # skill (native)
pi install npm:pi-mcp-adapter                                               # one-time, for MCP
```

`~/.config/mcp/mcp.json` (same `mcpServers` schema as our `.mcp.json`):

```json
{
  "settings": { "toolPrefix": "none" },
  "mcpServers": { "freeglm-<cap>": {
    "command": "uvx",
    "args": ["--from", "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1", "freeglm-<cap>"]
  } }
}
```

Do not add a generic `directTools` list: tool names differ by capability. The server inherits real process environment values and independently reads `~/.freeglm/config`, so omitting `env` also avoids an empty interpolation masking a configured key. Skill-only capabilities (edu-agent) work with just the skill copy. Headless: `pi -p "…"`.

### QwenPaw 2.0

QwenPaw 2.0 has no plugin marketplace of its own, so it can only be installed manually. Replace `<agent_id>` with the active agent/workspace id (`default` for the default agent) and `<cap>` with the capability:

```bash
# 1) skill
cp -r src/capabilities/<cap>/skill ~/.qwenpaw/workspaces/<agent_id>/skills/freeglm-<cap>
qwenpaw skills list      # triggers reconcile, registering it in the manifest (disabled at this point)
qwenpaw skills config    # interactively check to enable
# 2) MCP: add it to mcp.clients in ~/.qwenpaw/workspaces/<agent_id>/agent.json (no CLI — edit the file directly; hot-reloaded)
```

```json
{
  "mcp": {
    "clients": {
      "freeglm-<cap>": {
        "name": "freeglm-<cap>",
        "enabled": true,
        "transport": "stdio",
        "command": "uvx",
        "args": ["--from", "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1", "freeglm-<cap>"]
      }
    }
  }
}
```

### ZCode

ZCode is a Claude-compatible plugin marketplace harness and ships no plugin CLI on `PATH`. In an
open workspace, use the actual UI flow: open **Settings → Plugins**, click **Create → Add
marketplace**, enter `https://github.com/yenns7/freeglm.git`, then find `freeglm-<cap>` in the
Personal marketplace and click **Install**. Use the marketplace source panel's **Refresh** action
when a newer version is published.

The repository is zcode-ready out of the box:

- a root `.zcode-plugin/marketplace.json` (Claude-schema marketplace, `owner` = `yenns7`), and
- a per-capability `.zcode-plugin/plugin.json` (`name`/`skills`/`mcpServers`, `author` = `yenns7`).

Each plugin's `mcpServers` launches the server on demand via `uvx --from "freeglm[<cap>] @
git+…" freeglm-<cap>` (no manual pip), and its `skills` point at `./skill`. Install `core` by
default (local I/O base) plus whichever others you need; see the
[ZCode adaptation guide](adapting_zcode.md) for how this works under the hood and how to
replicate it for another harness.

## Dependencies

`uvx` installs the Python dependencies for the chosen profile into an isolated cache on first launch. Only two things are prepared manually.

### API keys (only for API-based tools)

The VL tools (`vision_chat` / `ocr` / `grounding`) need `DASHSCOPE_API_KEY` **or** `ZHIPU_API_KEY` — set only the Zhipu key and the VL tools auto-route to the GLM-4.6V-Flash backend (zero DashScope config). `transcribe_audio` and the generation tools still require `DASHSCOPE_API_KEY`. Keys are inherited from the shell environment (or `~/.freeglm/config`). The web tools (`web_search` / `web_extractor` / `image_search`) use the Serper API and require `SERPER_API_KEY` instead. Native image/video/document reading needs no key.

### System tools (install manually with your system package manager)

| Tool | Powers | Install |
|------|-----------|------|
| **ffmpeg** | `read_video` / `transcribe_audio` / video-memory / video-edit | `apt install ffmpeg`  ·  `brew install ffmpeg` |
| **libreoffice** | Office / DrawIO in `visualize` | `apt install libreoffice`  ·  `brew install --cask libreoffice` |
| **blender** | high-quality 3D rendering in `visualize` (optional, falls back to matplotlib by default) | `apt install blender`  ·  `brew install --cask blender` |
| **texlive** (pdflatex) | LaTeX in `visualize` | `apt install texlive-latex-base texlive-latex-extra` |
| **chromium** (playwright) | web-page screenshots in `visualize` | `playwright install chromium` |

How to see which system tools are missing:

- Check with uvx: `uvx --from "freeglm[all] @ git+https://github.com/yenns7/freeglm.git@v1.0.1" freeglm-<cap> --check-system`.
- At server startup, if an installed extra is missing its system tool, a warning line is printed to stderr.
- At actual tool-call time, you get a "please install X" text message, while other tools keep working.

### edu-agent exception: skill-only, deps prepared manually

`freeglm-edu-agent` is a **pure skill** (no MCP server), so "installing a plugin needs no manual pip" does **not** apply — `uvx` installs nothing for it, and its runtime deps must be prepared by hand:

| Dependency | Powers | Install / check |
|------|--------|-----------------|
| **Node.js + npm/npx** (≥18) | scaffold + render (`npx hyperframes`) | `node -v` |
| **hyperframes CLI** | `init` / `lint` / `validate` / `render` | pulled on demand by `npx hyperframes` (needs npm-registry access to scaffold; version pinned in-project afterward) |
| **Headless Chromium + OS libs** | `npx hyperframes render` (puppeteer) + post-render QA gates | auto-downloaded by puppeteer on first `npx hyperframes`; on minimal Linux also `apt install libnss3 libatk-bridge2.0-0 libgbm1 libasound2 libxkbcommon0 libgtk-3-0 fonts-noto-cjk` (else Chrome won't launch / CJK renders as tofu). Reuse a system Chrome via `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium` |
| **Python** `dashscope` `soundfile` `numpy` `requests` | Step-3 TTS synth + stitch | `python3 -m pip install dashscope soundfile numpy requests` |
| **ffmpeg** | loudness normalize (`loudnorm`) + post-render frame self-check | `apt install ffmpeg` · `brew install ffmpeg` |
| **`DASHSCOPE_API_KEY`** | Qwen-TTS (`qwen3-tts-flash`) | inherited from the shell |

> Network boundary: `npx hyperframes init` and the TTS calls need internet; the **render itself is offline** (so fonts / KaTeX / GSAP are self-hosted into `dist/`). Full checklist: the skill's `SKILL.md` → "Prerequisites".

### Common environment variables

Config is read from the shell environment, falling back to the installer-managed `~/.freeglm/config` when a variable is absent, so GUI-launched harnesses pick it up too. Configure credentials interactively with `bash install.sh configure` (or `<entry> --setup`); do not paste secret values into commands or documentation. Automation may provide the common environment variable names below through its secret store. This table is intentionally not exhaustive: [`install.sh`](../../install.sh) `CONFIG_SPEC`, browsable through `bash install.sh configure`, is the executable complete catalog and is kept in sync with the runtime.

| Variable | Used by | Default |
|---|---|---|
| `DASHSCOPE_API_KEY` | vision_chat · ocr · grounding (Qwen backend) · transcribe_audio · generation · video-memory build | *(required for these)* |
| `ZHIPU_API_KEY` | vision_chat · ocr · grounding — GLM-4.6V-Flash backend; auto-selected when set alone | *(required for the Zhipu backend)* |
| `ZHIPU_BASE_URL` | override the Zhipu endpoint | Zhipu compat URL |
| `ZHIPU_VISION_MODEL` | default VL model for the Zhipu backend | `glm-4.6v-flash` |
| `SERPER_API_KEY` | web_search · web_extractor · image_search | *(required for these)* |
| `DASHSCOPE_BASE_URL` | override the DashScope endpoint | DashScope compat URL |
| `SAM3_SERVER_URL` | `segmentation` (SAM3 server) | *(required for segmentation)* |
| `ASR_SERVER_URLS` | `transcribe_audio` self-hosted fallback (comma-separated, round-robined) when DashScope fails | *unset → DashScope only* |
| `FREEGLM_FFMPEG_TIMEOUT` | ffmpeg timeout, seconds | `120` |
| `FREEGLM_CHAT_TIMEOUT` | OpenAI-compatible chat request timeout, seconds | `600` |
| `FREEGLM_MAX_TOTAL_FRAMES` | max frames sampled from a video | `600` |
| `FREEGLM_CACHE` | cache dir for derived render artifacts | OS cache dir |
| `FREEGLM_CONFIG_DIR` | override the config dir that GUI harnesses read for keys | `~/.freeglm` |
| `FREEGLM_CONFIG` | override the full config-file path | `<config dir>/config` |

> **blender / freecad** are thin clients — they connect to a **running** Blender / FreeCAD carrying the bundled addon. `FREEGLM_AUTOLAUNCH=1` (preset in the plugin manifests) brings the app up on the first tool call, auto-downloading it on Linux-x86_64 if missing. See [`cookbooks/blender`](../../cookbooks/blender/usage.md) / [`cookbooks/freecad`](../../cookbooks/freecad/usage.md) for the full setup, env vars, and troubleshooting.

## Repository layout

```
src/
├── capabilities/            #   one directory per capability (may contain a skill and/or its companion MCP tools)
│   ├── core/                #     local I/O: read_image / read_video / visualize / crop / draw_bbox / …
│   ├── api/                 #     cloud media understanding: vision_chat / ocr / grounding / Omni / ASR / segmentation
│   ├── video-memory/        #     long-video memory: hierarchical graph + semantic search
│   ├── video-edit/          #     video editing + image/video/audio generation
│   ├── blender/             #     Blender thin client (bundled addon: vendor/ + --launch-app)
│   ├── freecad/             #     FreeCAD thin client (bundled addon: vendor/ + --launch-app)
│   └── example/             #     template: skill + tools
├── shared/                  #   shared library (reusable code: env/content/image/video/cache/syscmd/api_openai/api_dashscope …)
└── mcp_framework.py         #   shared framework (tool auto-registration + FastMCP serve)
pyproject.toml               # the single distribution freeglm (entries / extras / version)
.claude-plugin/  tests/  ruff.toml   # .claude-plugin/marketplace.json = the native plugin marketplace
```
