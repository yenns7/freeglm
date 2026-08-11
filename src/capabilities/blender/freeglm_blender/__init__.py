"""FreeGLM Blender capability — a thin MCP client for a live Blender + blender-mcp addon.

Ported from blender-mcp (MIT, © Siddharth Ahuja — https://github.com/ahujasid/blender-mcp);
telemetry removed and adapted onto FreeGLM' mcp_framework. These tools are a stdio MCP
server that connects over TCP to a *running* Blender instance carrying the vendored addon (bundled
in vendor/, see skill/SKILL.md). This process does NOT launch Blender as part of serving — start it
yourself, or run `freeglm-blender --launch-app` (brings up Blender + the bundled addon).
"""

import sys

from mcp_framework import __version__ as __version__
from mcp_framework import build_registry

SPECS, get_handler, list_tools = build_registry(__name__, ["tools"])

# System tools pip/uv cannot install. NOTE: these tools are a THIN CLIENT — Blender may even run on
# another host. --check-system can only probe binaries on PATH, so every entry is report-only
# (startup=False); real readiness is the live session, checked by on_start() / the skill.
_BLENDER_TOOLS = ["blender"]
if sys.platform == "darwin":
    _BLENDER_TOOLS.append("/Applications/Blender.app/Contents/MacOS/Blender")

SYSTEM_DEPS = [
    {
        "label": "Blender (host that runs the live session the tools connect to)",
        "tools": _BLENDER_TOOLS,
        "hint": "auto-downloaded on Linux-x86_64 by `--launch-app` / FREEGLM_AUTOLAUNCH (pinned 4.2.x), "
        "else `apt install blender` | `brew install --cask blender`",
        "startup": False,
    },
]
if sys.platform == "linux":
    SYSTEM_DEPS.append(
        {
            "label": "xvfb (headless display — commands do NOT execute under 'blender -b')",
            "tools": ["xvfb-run"],
            "hint": "apt install xvfb (needs root — the one step auto-download can't do; skip on a real display with --gui)",
            "startup": False,
        }
    )

SYSTEM_DEPS_NOTE = (
    "These tools are a THIN CLIENT: they connect to a running Blender + blender-mcp addon at "
    "$BLENDER_HOST:$BLENDER_PORT (default localhost:9876). --check-system only checks binaries on "
    "PATH — it cannot verify the live session. Bring one up with `freeglm-blender "
    "--launch-app` (add --gui on a desktop); it auto-downloads Blender 4.2.x on Linux-x86_64 if it's "
    "missing (FREEGLM_NO_AUTO_INSTALL disables that). On headless Linux, install xvfb; other "
    "platforms launch the native GUI directly. See the freeglm-blender skill."
)

USAGE_NOTE = (
    "Connects to a running Blender instance (blender-mcp addon) at $BLENDER_HOST:$BLENDER_PORT "
    "(default localhost:9876). Start one with `freeglm-blender --launch-app` (the bundled "
    "addon ships with this package), or launch Blender yourself — see SKILL.md."
)


def launch_app(argv):
    """`--launch-app`: bring up a live Blender + the bundled addon (see _launch.py)."""
    from ._launch import launch_app as _impl

    return _impl(argv)


def on_start():
    from .loader import probe

    probe()
