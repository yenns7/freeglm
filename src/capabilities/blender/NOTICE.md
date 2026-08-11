# Third-party attribution — Blender capability

This capability ports and vendors code from **blender-mcp**.

- Upstream: blender-mcp — https://github.com/ahujasid/blender-mcp
- Copyright: (c) 2025 Siddharth Ahuja
- License: MIT — full text vendored at `freeglm_blender/vendor/LICENSE`

Vendored / derived files:

- `freeglm_blender/vendor/addon.py` — the in-Blender socket server + integrations, adapted
  from upstream (telemetry removed; an offscreen viewport-screenshot patch applied). The header
  retains the upstream copyright ("Code created by Siddharth Ahuja © 2025").
- `freeglm_blender/vendor/blender_startup.py` — startup shim that loads `addon.py` inside
  Blender.
- `freeglm_blender/loader.py` and `freeglm_blender/tools/*.py` — the MCP tool
  surface (tool names, parameters, and behavior) is ported from `blender_mcp/server.py`, adapted
  onto FreeGLM' `mcp_framework`. Telemetry was removed and the per-tool `user_prompt`
  parameter (telemetry-only) was dropped.

The MIT license text of the upstream project applies to the vendored/derived portions above.

## Related prior art (referenced, not vendored)

The Blender Foundation maintains a separate, official MCP server at
https://projects.blender.org/lab/blender_mcp — licensed **GPL-2.0-or-later** (Blender's default
license), distinct from the third-party `ahujasid/blender-mcp` above. This capability does **not**
incorporate any code from the official `lab/blender_mcp` project (the vendored addon and tool surface
are ahujasid's MIT-licensed `blender-mcp`); it is acknowledged here only as related work in the same
space. No GPL-licensed code ships in this distribution.
