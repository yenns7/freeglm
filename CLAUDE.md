# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FreeGLM is an Agent Skills + MCP Tools platform for vision-language models. Each capability lives in one directory under `src/capabilities/<name>/`, holding any of: a `skill/` (the Agent Skill) and a `<import_name>/` MCP-server package — each part optional. Main subsystems:

1. **freeglm-core** — Local file capability: read and visualize any file (images, video, PDF/Office, code, data, 3D, notebooks, GIS) via `read_image`/`read_video`/`media_info`/`visualize`, plus image tools (`crop`/`draw_bbox`/`save_view`). `src/capabilities/core/` (skill + `freeglm_core/` server).
2. **freeglm-api** — Cloud APIs for understanding media, split by model family into three subpackages (directory == category): `vl/` (`vision_chat`, `ocr`, `grounding` — two OpenAI-compatible backends via `shared.api_openai`: DashScope Qwen (default, `qwen3.7-plus`) or Zhipu GLM (`glm-4.6v-flash`, auto-selected when only `ZHIPU_API_KEY` is set, or per call `provider="zhipu"`; Zhipu has no video modality, so videos degrade to locally-sampled image frames there)), `omni/` (Qwen-Omni A/V: `omni_av_caption`, `omni_asr`/`omni_asr_timestamped`/`omni_multi_speaker_asr`, `omni_av_grounding`, `omni_av_counting`, `omni_music_caption` — via `shared.api_omni`, DashScope only), and `others/` (`transcribe_audio` — Qwen3-ASR, `segmentation` — SAM3); the non-VL families remain DashScope-only. 12 tools total. `src/capabilities/api/` (skill + `freeglm_api/` server).
3. **freeglm-search** — Web + reverse-image search to confirm facts: `web_search`, `web_extractor`, `image_search`; currently Serper. `src/capabilities/search/` (skill + `freeglm_search/` server).
4. **freeglm-video-memory** — Hierarchical graph memory for long video QA. 4-level tree: Root → SuperEvent → MacroEvent → Subgraph, with embedding-based semantic search. `src/capabilities/video-memory/` (skill + `freeglm_video_memory/` server).
5. **freeglm-video-edit** — Video-editing skill + image/video/audio **generation** MCP tools (DashScope, via `shared.api_dashscope`). `src/capabilities/video-edit/` (skill + `freeglm_video_edit/` server).
6. **freeglm-blender** — Blender 3D modeling: MCP tools driving a live Blender (execute Python, viewport screenshots, PolyHaven/Sketchfab/Hyper3D/Hunyuan3D assets) + a build→refine→verify skill; needs a running Blender + addon. `src/capabilities/blender/`.
7. **freeglm-freecad** — FreeCAD parametric CAD: MCP tools (create/edit objects, execute Python, named-view screenshots, parts library, CalculiX FEM) + a skill; needs a running FreeCAD + addon. `src/capabilities/freecad/`.
8. **freeglm-edu-agent** — Skill only: turns a math/science problem or image into a step-by-step Chinese explainer video or interactive page. `src/capabilities/edu-agent/`.
9. **freeglm-example** — Template capability (skill + server, 5 demo tools) to copy when adding your own. `src/capabilities/example/`.

## Video Routing

Route by task and duration instead of forcing every video through one path:

1. **Edit existing footage** → use `freeglm-video-edit`; add video-memory only when long footage needs whole-video semantic location.
2. **Content QA under 30 minutes** → inspect metadata, then use `freeglm-core` `read_video` with an appropriate sampling/window strategy.
3. **Whole-video QA at 30+ minutes or a multi-video directory** → use `freeglm-video-memory` first, then verify located segments with a narrow `read_video` window.
4. **External fact/identity verification** → save the relevant frame, then use `freeglm-search` with its data-egress consent rules.
5. Never answer a long-video question from a few thumbnails, and do not bypass the provided media tools with ad-hoc ffmpeg extraction.

The video-memory flow is: check existing memory → build if needed → query → visually verify the relevant time window.

## Common Commands

```bash
# Run MCP server (from source)
python3 src/capabilities/core/freeglm_core

# Install — via each harness's native plugin marketplace (reads .claude-plugin/marketplace.json; codex also .codex-plugin/)
claude plugin marketplace add <repo-url-or-path>
claude plugin install freeglm-core@freeglm

# Test MCP server
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n' | python3 src/capabilities/core/freeglm_core

# Tests / lint
python3 -m pytest tests/
ruff format . && ruff check . --fix
```

## Architecture

```
src/                                         # first-party code (shared library + all capabilities)
├── capabilities/                            # one dir per capability (skill and/or MCP server, each optional)
│   ├── core/                                # local file-I/O capability (skill + entry: freeglm-core)
│   │   ├── skill/                           #   Agent Skill (symlink target): SKILL.md + references/
│   │   └── freeglm_core/                  #   MCP server package (dir name == import name)
│   │       ├── __init__.py                  #     __version__ + SPECS (mcp_framework.build_registry) + SYSTEM_DEPS table + list_tools/on_start hooks
│   │       ├── __main__.py                  #     generic shim → mcp_framework.run_main (identical across servers)
│   │       ├── stdio_streaming.py           #     core-local streaming helper
│   │       ├── readers/                     #     image/video/media metadata readers
│   │       ├── producers/                   #     crop, draw_bbox, save_view
│   │       └── renderers/ visualizers/      #     file rendering + visualize tool
│   ├── video-memory/                        # long-video graph-memory capability
│   │   ├── skill/                           #   SKILL.md + build pipeline (self-contained, flat modules)
│   │   │   └── script/build_memory/         #     build_memory.sh, build_graph.py, pipeline_worker.py, llm_client.py,
│   │   │                                    #     prompts.py, schema.py + embeddings.py (copies of the server's)
│   │   └── freeglm_video_memory/     #   MCP server package
│   │       ├── __init__.py                  #     __version__ + SPECS + SYSTEM_DEPS table + list_tools/on_start hooks
│   │       ├── __main__.py                  #     generic shim → mcp_framework.run_main
│   │       ├── tools/                       #     one TOOL+handle per tool: get_summary, get_super_events, get_macro_events, get_subgraph, search_nodes, enumerate_events, search_ocr_text, search_asr_text, search_by_time
│   │       ├── loader.py                    #     shared MemoryToolkit load + cache (get_toolkit) used by every tool
│   │       ├── toolkit.py                   #     MemoryToolkit: retrieval methods (drill-down pattern)
│   │       ├── schema.py                    #     data model: HierarchicalGraphMemory, VideoRoot, SuperEvent, …
│   │       ├── embeddings.py                #     EmbeddingIndex (DashScope/local, cosine similarity, NPZ)
│   │       └── query_memory.py              #     CLI: query graph memory
│   ├── video-edit/                          # video-editing skill + generation MCP server
│   │   ├── skill/                           #   SKILL.md + workflows/
│   │   └── freeglm_video_edit/       #   MCP server package: tools/ = qwen_image, qwen_tts, wan_s2v, wan_t2v, happyhorse (DashScope generation, via shared.api_dashscope)
│   ├── blender/                             # Blender 3D-modeling capability (skill + server): thin MCP client → a live Blender + addon (execute Python, viewport screenshot, PolyHaven/Sketchfab/Hyper3D/Hunyuan3D assets)
│   ├── freecad/                             # FreeCAD parametric-CAD capability (skill + server): thin MCP client → a live FreeCAD + FreeCADMCP addon (create/edit objects, execute Python, named-view screenshot, parts library, CalculiX FEM)
│   ├── edu-agent/                           # educational explainer-video capability (skill only): a math/science problem or image → step-by-step Chinese video or interactive page
│   └── example/                             # example/template capability (skill + server + 5 demo tools: text/image/frames + API call + env/config) — walkthrough: docs/en/how_to_add_new_capability.md
├── shared/                                  # shared LIBRARY (env/content/image/video/cache/syscmd + api_openai/api_dashscope) — reusable by every server; no __main__/tools/entry
└── mcp_framework.py                         # shared framework: build_registry + tool_schema + serve (FastMCP) + run_main + system_report/startup_warnings (every server imports it)

pyproject.toml                         # the one distribution: entries, extras (Python deps), package map, version
.claude-plugin/marketplace.json        # native plugin marketplace (per-capability manifests live in each src/capabilities/<cap>/)
tests/  eval/  ruff.toml
```

**Naming convention**: one capability = a short folder `src/capabilities/<folder>/` (`core`, `video-memory`, `video-edit`, `blender`, `freecad`, `edu-agent`, `example`), holding any of `skill/` (the Agent Skill) and a `<import_name>/` MCP-server package (a valid Python identifier, e.g. `freeglm_core`). The skill, console entry, and plugin are all named `freeglm-<folder>` (e.g. `freeglm-core`) — matching the capability, so a skill's `SKILL.md` `name:` equals its install/plugin name; each capability is listed in `.claude-plugin/marketplace.json` for native install. Tests/launch find the server package by scanning each `src/capabilities/<folder>/` for the subdir with `__init__.py`. Skill and server are each optional — skill-only, mcp-only, or both.

**Adding a capability** (full walkthrough: `docs/en/how_to_add_new_capability.md` — copy `src/capabilities/example/`): create `src/capabilities/<folder>/` with `skill/` (`SKILL.md`) and/or `<import_name>/` (server package — copy `__main__.py` verbatim from an existing server; its `__init__.py` holds `__version__` + `SPECS, get_handler = build_registry(...)` + a `SYSTEM_DEPS` table (system tools pip can't install — the framework renders `--check-system` + startup warnings from it; each entry needs only `label`/`tools`/`hint`, with `extra`/`probe`/`startup` optional) + an optional `on_start()`; add tool modules, each exporting `TOOL` — with a Pydantic `args` model — plus `handle`). For a server, register it in `pyproject.toml` (a `[project.scripts]` entry, add its folder to `[tool.setuptools]` `package-dir` + `packages.find` `where` — subpackages are auto-discovered — and an extras group/profile); then add a plugin entry to `.claude-plugin/marketplace.json` and write the capability's `.claude-plugin/plugin.json` (skill + inline `mcpServers`, whose server key is `freeglm-<cap>` — unique per capability, since qwen-code namespaces MCP servers globally so a shared key like `main` would collide across capabilities), plus a `.codex-plugin/plugin.json` + `.mcp.json` if it should install under codex; install via the harness's native `plugin install`. Shared code goes in a module (or package) under `src/` with no `__main__.py` (bundled + importable, no console entry) — `mcp_framework.py` (the framework) and `shared/` (reusable library: `shared.env` config/constants + `get_env` (the one accessor that reads the environment), `shared.content` MCP content-block + input-guard helpers, `shared.image` PIL primitives + resolution math, `shared.video` ffmpeg frame extraction + timestamp parsing, `shared.cache` derived-artifact caching, `shared.syscmd` external-CLI location, `shared.api_openai` OpenAI-compatible chat client, `shared.api_dashscope` DashScope native-REST async-task helpers) are exactly that. Reuse those across capabilities instead of importing a sibling capability's server package (that only resolves once installed and couples them; from source it isn't even on `sys.path`).

**Packaging**: all MCP servers ship in ONE distribution — `freeglm`, from the repo-root `pyproject.toml` (hand-authored — it IS the source, nothing generates it). `[project.optional-dependencies]` holds the Python deps as **capability extras** (`api`/`search`/`viz`/`video-memory`/`video-edit`/`example`/`blender`/`freecad`) and **profiles** composed via self-reference (`core`=`viz`, local-only; `memory`=`core,video-memory`; `all`=`core,api,search,video-memory,video-edit,blender,freecad`). `[tool.setuptools]` `package-dir` + `packages.find` (`include="freeglm*"`) bundle each server package + its subpackages while excluding the sibling `skill/`. System tools (ffmpeg/blender/freecad/libreoffice/latex/chromium) are not pip-installable, so each server declares them in a `SYSTEM_DEPS` table and `mcp_framework` reports them via `<entry> --check-system`. Install requires uv and uses each harness's native plugin/extension mechanism. Config harnesses with a native install are automated by `install.sh`; opencode, pi, QwenPaw and ZCode follow the documented manual/UI paths. Credentials are inherited from the environment or `~/.freeglm/config`, never embedded in manifests or MCP arguments. Don't install the same capability two ways.

## Key Patterns

**Tool auto-discovery** (all servers, via the shared `mcp_framework` module): create a `.py` exporting `TOOL` (a dict with `name`, `description`, and a Pydantic `args` model) + `handle(arguments) -> list[content-dict]` in a scanned subpackage and it's auto-registered at server start — no manual registration. Each package's `__init__.py` calls `mcp_framework.build_registry(__name__, [subpackages])` → `SPECS` + `get_handler()` (`list_tools()` derives the wire metadata). `run_main` → `mcp_framework.serve(...)` bridges the specs onto the SDK's **FastMCP**: it synthesizes a typed wrapper per tool (signature from the `args` model, so FastMCP generates the `inputSchema` and validates every call), overrides the advertised schema with a normalized `tool_schema(args)` (auto-`title` stripped + `$ref` inlined — kept semantically identical to the old hand-written style), then runs `handle` in a worker thread (`anyio.to_thread`); `handle` still gets a plain dict and returns `{"type": "text"|"image", ...}` blocks. core scans `readers/`/`visualizers/`/`producers/`; api scans `vl/`/`omni/`/`others/` (by model family); search and video-memory scan `tools/`, the latter resolving the shared `MemoryToolkit` via `loader.get_toolkit()`. `mcp_framework` depends only on the `mcp` SDK (which bundles FastMCP), so it doesn't couple the servers to each other.

**Graph memory build phases** (`src/capabilities/video-memory/skill/script/build_memory/build_graph.py`; `build_memory.sh` orchestrates chunked P1+P2 then P3):
- P1: `step1_scene_detect_segmentation` — HLS frame-diff scene-cut segmentation into macro events
- P2: `step2_subgraph_extraction` — per-macro subgraph (entities/events/OCR/edges); parallelized by `pipeline_worker.py`
- P3: `step3_hierarchical_aggregation` — macros → supers → root, then `EmbeddingIndex` build

When OSS creds (`OSS_AK`/`OSS_SK`) are set the VLM gets clipped-video URLs (`clip_and_upload_video`); otherwise it falls back to inline base64 frames (`extract_frames_base64`), so a build needs only `DASHSCOPE_API_KEY`.

**Video preprocessing**: Videos ≤2048×2048 pixels are precompressed to 512p 1fps H.264 (`-g 1`) for fast seek. 8K+ videos skip preprocess (AV1 decode too slow).

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DASHSCOPE_API_KEY` | Required for vision_chat, ocr, grounding (Qwen backend), transcribe_audio, generation, graph-memory builds |
| `DASHSCOPE_BASE_URL` | Override the DashScope OpenAI-compatible base URL |
| `ZHIPU_API_KEY` | GLM-4.6V-Flash vision backend for vision_chat / ocr / grounding — when set alone (no DASHSCOPE_API_KEY), VL tools auto-route to Zhipu |
| `ZHIPU_BASE_URL` | Override the Zhipu OpenAI-compatible base URL (default: https://open.bigmodel.cn/api/paas/v4) |
| `ZHIPU_VISION_MODEL` | Default VL model for the Zhipu backend (default: glm-4.6v-flash) |
| `SERPER_API_KEY` | Required for web_search / web_extractor / image_search |
| `SAM3_SERVER_URL` | Required for segmentation (SAM3 server URL) |
| `ASR_SERVER_URLS` | Comma-separated self-hosted ASR server URLs (transcribe_audio fallback when DashScope fails) |
| `FREEGLM_FFMPEG_TIMEOUT` | ffmpeg timeout seconds (default: 120) |
| `FREEGLM_CHAT_TIMEOUT` | OpenAI-compatible chat request timeout seconds (default: 600) |
| `FREEGLM_MAX_TOTAL_FRAMES` | Max frames sampled from a video (default: 600) |
| `FREEGLM_CACHE` | Override the cache dir for derived render artifacts (default: OS cache dir) |
| `GRAPH_MEMORY_PATH` | graph_memory.json path (video-memory MCP server; takes precedence over a passed video path) |
| `EMBEDDINGS_PATH` | embeddings.npz path (video-memory MCP server) |
| `CUTOFF_SEC` | Optional time cutoff (seconds) for video-memory retrieval |

**OSS (optional)** — only needed to serve large videos/frames by signed URL instead of inline base64.

| Variable | Scope | Purpose |
|----------|-------|---------|
| `OSS_AK` / `OSS_SK` / `OSS_ENDPOINT` | shared | Credentials + endpoint |
| `OSS_BUCKET` | build / api | Upload-destination bucket for `upload_and_sign` (memory-build clips, api video/Omni oversized media) |
| `OSS_VIDEO_CLIP_PREFIX` | build / api | Key prefix for uploaded clips (default: `tmp/video_clips`) |
| `OSS_URL_EXPIRY` | shared | Signed-URL TTL seconds (default: 7200) |

**App hosts (optional)** — blender/freecad live sessions + edu-agent rendering. Full catalog: `src/shared/env.py` `CONFIG_FIELDS` (regenerate these tables via `python3 scripts/gen_env_docs.py`).

| Variable | Scope | Purpose |
|----------|-------|---------|
| `BLENDER_BINARY` / `BLENDER_HOST` / `BLENDER_PORT` | blender | Blender executable + addon host/port (default: localhost:9876) |
| `FREECAD_BINARY` / `FREECAD_RPC_HOST` / `FREECAD_RPC_PORT` / `FREECAD_MOD_DIR` | freecad | FreeCAD executable + RPC host/port (default: localhost:9875) + Mod dir for the bundled addon |
| `NODE_PATH` / `PUPPETEER_EXECUTABLE_PATH` | edu-agent | Node.js module resolution path / headless Chromium executable for Puppeteer |
