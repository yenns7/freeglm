#!/usr/bin/env bash
# Debug the full native plugin path (marketplace add + plugin install) against your LOCAL working
# tree instead of git@main: point a capability's plugin manifests at file://<repo> (with uvx
# --refresh so every launch rebuilds from your source), install, test, then revert.
# `marketplace add <this repo dir>` reads the working-tree manifests, so local wins.
#
#   scripts/dev-plugin.sh <cap>            # flip <cap>'s manifests → local (file:// + --refresh)
#   scripts/dev-plugin.sh <cap> --revert   # restore the manifests (git checkout)
#     <cap> = core | video-memory | video-edit | example
#
# --refresh makes uvx rebuild the local package on every launch (a bit slower, but always current).
# For rapid server-code iteration prefer `claude mcp add <name> -- python3 <server-dir>` instead
# (no build step at all — see docs/en/local_development.md).
set -euo pipefail
repo="$(cd "$(dirname "$0")/.." && pwd)"
cap="${1:?usage: dev-plugin.sh <cap> [--revert]   (cap = core|video-memory|video-edit|example)}"

files=()
for f in "$repo/src/capabilities/$cap/.claude-plugin/plugin.json" "$repo/src/capabilities/$cap/.mcp.json"; do
    [ -f "$f" ] && files+=("$f")
done
[ ${#files[@]} -gt 0 ] || { echo "no plugin manifests found for capability '$cap'"; exit 1; }

if [ "${2:-}" = "--revert" ]; then
    git -C "$repo" checkout -- "${files[@]}"
    echo "✓ reverted $cap manifests"
    exit 0
fi

REPO="$repo" python3 - "${files[@]}" <<'PY'
import json, os, sys

repo = os.environ["REPO"]
git_ref = "git+https://github.com/yenns7/freeglm.git@main"
local = f"file://{repo}"
for path in sys.argv[1:]:
    data = json.load(open(path))
    for srv in data.get("mcpServers", {}).values():
        args = [a.replace(git_ref, local) for a in srv.get("args", [])]
        if "--refresh" not in args:
            args.insert(0, "--refresh")
        srv["args"] = args
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
PY

echo "✓ flipped $cap manifests → $repo  (file:// + uvx --refresh)"
echo "  claude plugin marketplace add $repo"
echo "  claude plugin install freeglm-$cap@freeglm"
echo "  # revert when done:  scripts/dev-plugin.sh $cap --revert"
