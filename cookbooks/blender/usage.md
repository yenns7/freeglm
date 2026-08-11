# Cookbook — FreeGLM Blender

Driving a **real, running** Blender from a prompt with `freeglm-blender`: the model models
the scene, lights it, renders with Cycles, writes the project file to disk, and returns screenshots.
See the [Cases](#cases) below. (For parametric CAD, see [cookbooks/freecad](../freecad/usage.md).)

> This capability connects to a **running** Blender carrying the bundled addon. You don't start it by
> hand — after installing, the first query brings it up automatically (on Linux it also auto-downloads
> the app if missing). It needs **no API key** (some asset/generation back-ends have their own keys,
> set inside Blender).

---

## Tools

Thin client: the tools talk to a live Blender carrying the bundled blender-mcp addon.
`FREEGLM_AUTOLAUNCH=1` (preset in the plugin manifests) brings Blender up on the first tool call,
auto-downloading it on Linux-x86_64 if missing; otherwise start it with
`freeglm-blender --launch-app`.

**Scene & code**
- `execute_blender_code` — run arbitrary Python in Blender (the workhorse)
- `get_scene_info` — summarize the current scene
- `get_object_info` — inspect one object
- `get_viewport_screenshot` — capture the viewport

**PolyHaven assets**
- `get_polyhaven_status`, `get_polyhaven_categories`, `search_polyhaven_assets`, `download_polyhaven_asset`, `set_texture`

**Sketchfab models**
- `get_sketchfab_status`, `search_sketchfab_models`, `get_sketchfab_model_preview`, `download_sketchfab_model`

**Hyper3D / Rodin generation**
- `get_hyper3d_status`, `generate_hyper3d_model_via_text`, `generate_hyper3d_model_via_images`, `poll_rodin_job_status`, `import_generated_asset`

**Hunyuan3D generation**
- `get_hunyuan3d_status`, `generate_hunyuan3d_model`, `poll_hunyuan_job_status`, `import_generated_asset_hunyuan`

---

## Install

```bash
claude plugin marketplace add https://github.com/yenns7/freeglm.git
claude plugin install freeglm-core@freeglm
claude plugin install freeglm-blender@freeglm
```

On a **headless server** (a cloud host / SSH with no display), one extra step (needs root):

```bash
sudo apt install xvfb
```

> Skip this on a desktop with a real display.

## Environment variables (usually none needed)

| Variable | Purpose | Default |
|----------|---------|---------|
| `BLENDER_HOST` / `BLENDER_PORT` | connection target | `localhost` / `9876` |
| `FREEGLM_AUTOLAUNCH` | set to `1` to launch Blender on the first tool call | off (preset to `1` in the plugin manifests) |
| `FREEGLM_NO_AUTO_INSTALL` | set to `1` to disable auto-download when the app is missing | off (auto-download by default) |
| `FREEGLM_CACHE` | where auto-downloaded apps live | OS cache dir |
| `BLENDER_BINARY` | path to the Blender binary (else search PATH, else auto-download) | unset |

> On non-Linux-x86_64 platforms (auto-download only covers Linux-x86_64), install Blender 4.2.x
> yourself and put it on PATH, or point at it with `BLENDER_BINARY`.

> Set these via env vars, `~/.freeglm/config`, or the guided installer **`bash install.sh`** (`bash install.sh verify` checks what's set).

---

## Cases

No case recorded yet. Add one in either style — see [core](../core/usage.md) for worked examples of both:

- **Trace** — a full session rendered to a self-contained HTML page, linked by URL.
- **Result** — the query plus a public link to the produced artifact (video / model / file) and/or a preview screenshot.

---

## Troubleshooting

- **Can't connect / first call is slow**: the first call downloads Blender (~300 MB) in the
  background and starts it — wait 1–2 min; subsequent queries connect instantly.
- **Headless machine reports xvfb errors**: `sudo apt install xvfb` (needs root). Not needed with a
  real display.
- **PolyHaven / Sketchfab / Hyper3D tools report "disabled"**: those asset / generation services
  need their own API key configured app-side (PolyHaven is free); leaving them unset doesn't affect
  anything else.

## Attribution & License

- **blender** is ported from [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp) (MIT)
- We also acknowledge the official Blender [projects.blender.org/lab/blender_mcp](https://projects.blender.org/lab/blender_mcp) (GPL-2.0-or-later, referenced only — none of its code is used)

Full third-party licenses are in the capability's `NOTICE.md`.
