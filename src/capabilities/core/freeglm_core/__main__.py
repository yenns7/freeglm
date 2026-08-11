"""Generic entry point for a FreeGLM MCP server.

Resolves the server package from this directory's name and delegates to mcp_framework.
Runnable as installed console script, `python3 -m <import_name>`, or from source.
"""

import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
_IMPORT = _PKG_DIR.name

# Run-from-source: make this package and mcp_framework importable.
if _IMPORT not in sys.modules:
    sys.path.insert(0, str(_PKG_DIR.parent))
    sys.path.insert(0, str(_PKG_DIR.parents[2]))


def main() -> None:
    """Console-script / module entry point."""
    from mcp_framework import run_main

    run_main(_IMPORT)


if __name__ == "__main__":
    main()
