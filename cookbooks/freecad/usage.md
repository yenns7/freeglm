# Cookbook — FreeGLM FreeCAD

Driving a **real, running** FreeCAD from a prompt with `freeglm-freecad`: the model builds a
parametric part, cuts geometry with booleans, and exports STEP/STL. See the [Cases](#cases) below.
(For 3D modeling / rendering, see [cookbooks/blender](../blender/usage.md).)

> This capability talks XML-RPC to a **running** FreeCAD carrying the bundled FreeCADMCP addon. You
> don't start it by hand — after installing, the first query brings it up automatically (on Linux it
> also auto-downloads the app if missing). It needs **no API key**.

---

## Tools

Thin client: the tools talk XML-RPC to a live FreeCAD carrying the bundled FreeCADMCP addon.
`FREEGLM_AUTOLAUNCH=1` (preset in the plugin manifests) brings FreeCAD up on the first tool call,
auto-downloading it on Linux-x86_64 if missing; otherwise start it with
`freeglm-freecad --launch-app`.

**Documents**
- `create_document`, `list_documents`, `reload_document`

**Objects**
- `create_object`, `edit_object`, `delete_object`, `get_object`, `get_objects`

**Parts library**
- `get_parts_list`, `insert_part_from_library`

**Views & code**
- `get_view` — screenshot a named standard view
- `execute_code`, `execute_code_async` — run Python in FreeCAD

**FEM**
- `run_fem_analysis` — run a finite-element analysis (needs CalculiX)

---

## Install

```bash
claude plugin marketplace add https://github.com/yenns7/freeglm.git
claude plugin install freeglm-core@freeglm
claude plugin install freeglm-freecad@freeglm
```

On a **headless server** (a cloud host / SSH with no display), one extra step (needs root):

```bash
sudo apt install xvfb
```

> Skip this on a desktop with a real display.

## Environment variables (usually none needed)

| Variable | Purpose | Default |
|----------|---------|---------|
| `FREECAD_RPC_HOST` / `FREECAD_RPC_PORT` | connection target | `localhost` / `9875` |
| `FREEGLM_AUTOLAUNCH` | set to `1` to launch FreeCAD on the first tool call | off (preset to `1` in the plugin manifests) |
| `FREEGLM_NO_AUTO_INSTALL` | set to `1` to disable auto-download when the app is missing | off (auto-download by default) |
| `FREEGLM_CACHE` | where auto-downloaded apps live | OS cache dir |
| `FREECAD_BINARY` | path to the FreeCAD binary (else search PATH, else auto-download) | unset |
| `FREECAD_MOD_DIR` | override where `--launch-app` installs the bundled addon | per-user FreeCAD Mod dir |
| `FREECAD_ONLY_TEXT_FEEDBACK` | make screenshot-bearing tools return text only | off |
| `FREECAD_MCP_HEADLESS` | set to `1` to run GUI operations headless (no FreeCAD GUI) | off |

> On non-Linux-x86_64 platforms (auto-download only covers Linux-x86_64), install FreeCAD 1.1.x
> yourself and put it on PATH, or point at it with `FREECAD_BINARY`.

> Set these via env vars, `~/.freeglm/config`, or the guided installer **`bash install.sh`** (`bash install.sh verify` checks what's set).

---

## Cases

No case recorded yet. Add one in either style — see [core](../core/usage.md) for worked examples of both:

- **Trace** — a full session rendered to a self-contained HTML page, linked by URL.
- **Result** — the query plus a public link to the produced artifact (video / model / file) and/or a preview screenshot.

---

## Troubleshooting

- **Can't connect / first call is slow**: the first call downloads FreeCAD (~1 GB) in the background
  and starts it — wait 1–2 min; subsequent queries connect instantly.
- **Headless machine reports xvfb errors**: `sudo apt install xvfb` (needs root). Not needed with a
  real display.
- **FEM won't run**: it needs the CalculiX solver: `sudo apt install calculix-ccx`.

## Attribution & License

- **freecad** is ported from [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) (MIT)

Full third-party licenses are in the capability's `NOTICE.md`.
