#!/usr/bin/env python3
"""Blender startup script — loads blender-mcp addon and configures the TCP port.

Invoked by: xvfb-run -a <blender> --python blender_startup.py

Environment variables:
  BLENDER_PORT           TCP port for the addon server (default 9876)
  BLENDER_MCP_ADDON_PATH Path to the blender-mcp addon.py file
"""

import bpy
import os
import sys

port = int(os.environ.get("BLENDER_PORT", "9876"))
addon_path = os.environ.get(
    "BLENDER_MCP_ADDON_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "addon.py"),
)

if not os.path.isfile(addon_path):
    print(f"[startup] ERROR: addon not found at {addon_path}", file=sys.stderr)
    sys.exit(1)

print(f"[startup] Loading blender-mcp addon from {addon_path}")
print(f"[startup] Target port: {port}")

# exec(addon.py) in the current namespace.
# Since __name__ == "__main__", the addon's `if __name__ == "__main__": register()`
# guard will fire, registering all classes and auto-starting the server on port 9876.
exec(open(addon_path, encoding="utf-8").read())

# If a custom port is requested, stop the default server and restart on the new port.
if port != 9876 and hasattr(bpy.types, "blendermcp_server"):
    print(f"[startup] Restarting server on port {port} ...")
    bpy.types.blendermcp_server.stop()
    # BlenderMCPServer is now in global scope from the exec'd addon code.
    bpy.types.blendermcp_server = BlenderMCPServer(port=port)  # noqa: F821
    bpy.types.blendermcp_server.start()

# Enable PolyHaven (free CC0 asset library) by default.
try:
    bpy.context.scene.blendermcp_use_polyhaven = True
    print("[startup] PolyHaven enabled")
except AttributeError:
    pass

print(f"[startup] Ready — Blender MCP server listening on port {port}")
# Blender stays in interactive mode after --python finishes (no sys.exit).
