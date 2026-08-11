"""Guards against silent drift between intentionally-duplicated files.

- The video-memory build pipeline keeps byte-identical copies of schema.py and
  embeddings.py (it runs as flat modules, separate from the installed server
  package). These must not diverge.
- Both server packages re-export mcp_framework.__version__ (the single distribution
  version source); this guards that the re-export stays wired.
"""

import json
import pathlib

import pytest
from conftest import REPO_ROOT

_ROOT = pathlib.Path(REPO_ROOT)
_CAP = _ROOT / "src" / "capabilities" / "video-memory"
_SERVER_DIR = _CAP / "freeglm_video_memory"
_BUILD_DIR = _CAP / "skill" / "script" / "build_memory"


@pytest.mark.parametrize("fname", ["schema.py", "embeddings.py"])
def test_build_copies_stay_identical(fname):
    server_copy = _SERVER_DIR / fname
    build_copy = _BUILD_DIR / fname
    assert server_copy.read_bytes() == build_copy.read_bytes(), (
        f"{fname} drifted between the video-memory server package and its build-pipeline copy.\n"
        f"  server: {server_copy}\n  build:  {build_copy}\n"
        f"They must stay byte-identical (the builder writes what the server reads). Re-sync them, "
        f"or, if you intentionally forked them, drop this guard."
    )


def test_all_packages_share_one_version():
    import freeglm_core
    import freeglm_video_memory
    import mcp_framework

    assert freeglm_core.__version__ == mcp_framework.__version__, (
        "freeglm_core must re-export mcp_framework.__version__ (the single version source)."
    )
    assert freeglm_video_memory.__version__ == mcp_framework.__version__, (
        "freeglm_video_memory must re-export mcp_framework.__version__ (the single version source)."
    )


# ── manifest sync across the four harness formats + marketplace (F2) ──
# Each capability hand-maintains .claude-plugin / .codex-plugin / .qoder-plugin / .mcp.json.
# These guard that name, version, and the uvx launch spec stay in agreement across a capability's
# own harness manifests (description is intentionally per-harness display text and is NOT checked).
# Versions are PER-CAPABILITY and independent of the distribution mcp_framework.__version__: bump a
# cap's version when its plugin layer (skill / manifest / .mcp.json launch spec) changes, so users'
# `plugin update` re-fetches it. Server-only Python changes ride the uvx `@main` ref and need no bump.

_CAPS_DIR = _ROOT / "src" / "capabilities"


def _capabilities() -> list[str]:
    return sorted(p.parent.parent.name for p in _CAPS_DIR.glob("*/.claude-plugin/plugin.json"))


def _load(cap: str, rel: str) -> dict:
    return json.loads((_CAPS_DIR / cap / rel).read_text())


def _server_capabilities() -> list[str]:
    """Caps that ship an MCP server — i.e. carry a .mcp.json launch spec. Skill-only caps
    (e.g. edu-agent) don't, so the launch-spec reconciliation below doesn't apply to them."""
    return [c for c in _capabilities() if (_CAPS_DIR / c / ".mcp.json").exists()]


@pytest.mark.parametrize("cap", _capabilities())
def test_manifest_name_and_version_agree(cap):
    manifests = {
        "claude": _load(cap, ".claude-plugin/plugin.json"),
        "codex": _load(cap, ".codex-plugin/plugin.json"),
        "qoder": _load(cap, ".qoder-plugin/plugin.json"),
    }
    names = {m["name"] for m in manifests.values()}
    assert len(names) == 1, f"{cap}: plugin name differs across harness manifests: {names}"
    # Version is per-capability (drives `plugin update`) and independent of the distribution
    # mcp_framework.__version__; only require a cap's three harness manifests to agree with each other.
    versions = {label: m["version"] for label, m in manifests.items()}
    assert len(set(versions.values())) == 1, (
        f"{cap}: plugin version differs across its harness manifests: {versions}. "
        "Bump a capability's claude/codex/qoder manifests together."
    )


@pytest.mark.parametrize("cap", _server_capabilities())
def test_mcp_launch_spec_agrees(cap):
    # codex/qoder reference ./.mcp.json; the .claude-plugin inlines the same server. They must
    # match. The two files label the sole server differently (.claude-plugin uses "main", .mcp.json
    # uses the capability name), so compare the single server entry's launch args by value.
    def _sole_server_args(spec: dict) -> list:
        servers = spec["mcpServers"]
        assert len(servers) == 1, f"{cap}: expected exactly one mcpServers entry, got {sorted(servers)}"
        return next(iter(servers.values()))["args"]

    claude_args = _sole_server_args(_load(cap, ".claude-plugin/plugin.json"))
    mcp_args = _sole_server_args(_load(cap, ".mcp.json"))
    assert claude_args == mcp_args, (
        f"{cap}: uvx launch args drifted between .claude-plugin (inline) and .mcp.json:\n"
        f"  claude: {claude_args}\n  mcp:    {mcp_args}"
    )


def test_marketplace_lists_every_capability():
    import mcp_framework

    market = json.loads((_ROOT / ".claude-plugin" / "marketplace.json").read_text())
    listed = {p["name"] for p in market["plugins"]}
    # `example` is a copy-me template that ships in the repo but is intentionally NOT published to
    # the marketplace (end users shouldn't see a demo plugin). Every other capability must be listed.
    TEMPLATE_ONLY = {"freeglm-example"}
    from_manifests = {_load(cap, ".claude-plugin/plugin.json")["name"] for cap in _capabilities()}
    assert listed == from_manifests - TEMPLATE_ONLY, (
        "marketplace.json plugins must match the capability manifests (minus template-only caps).\n"
        f"  marketplace: {sorted(listed)}\n  manifests:   {sorted(from_manifests)}\n"
        f"  template-only (excluded): {sorted(TEMPLATE_ONLY)}"
    )
    assert market["metadata"]["version"] == mcp_framework.__version__, (
        "marketplace.json metadata.version must track mcp_framework.__version__."
    )
