#!/usr/bin/env bash
# Editable-install freeglm into the active environment, so you can `import freeglm_core`
# (and the other capability packages) and run pytest / ad-hoc python against your working tree.
# Code edits are picked up live; re-run only when dependencies change.
#
#   scripts/dev-install.sh          # base deps only (import + run servers from source)
#   scripts/dev-install.sh core     # vision + full visualize
#   scripts/dev-install.sh all      # everything (heavy: geopandas/trimesh/playwright/pandas…)
set -euo pipefail
cd "$(dirname "$0")/.."

extras="${1:-}"
spec="."
[ -n "$extras" ] && spec=".[$extras]"

if command -v uv >/dev/null 2>&1 && [ -n "${VIRTUAL_ENV:-}" ]; then
    uv pip install -e "$spec"
else
    python3 -m pip install -e "$spec"
fi

echo "✓ editable-installed freeglm${extras:+[$extras]}"
echo "  try: python -c 'import freeglm_core as p; print(len(p.SPECS), \"tools\")'"
