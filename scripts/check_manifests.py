#!/usr/bin/env python3
"""Cross-check plugin manifests: marketplace.json ↔ per-capability manifests ↔ pyproject.toml.

For every capability under src/capabilities/<cap>/ this verifies the naming convention
(capability name / plugin name / MCP-server key / console entry are all `freeglm-<cap>`)
and that the three registration surfaces agree:

- .claude-plugin/marketplace.json — each plugin's name matches its source dir, the dir exists and
  carries a .claude-plugin/plugin.json; the marketplace metadata version matches mcp_framework.
- src/capabilities/<cap>/{.claude-plugin,.codex-plugin,.qoder-plugin}/plugin.json (+ .mcp.json) —
  same name, same version (== mcp_framework.__version__); for capabilities with an MCP-server
  package, the mcpServers key AND the uvx entry are exactly `freeglm-<cap>`, codex/qoder
  manifests reference the companion .mcp.json; skill-only capabilities declare no MCP server.
- pyproject.toml — [project.scripts] has `freeglm-<cap> = "<import_name>.__main__:main"`
  and [tool.setuptools.package-dir] maps <import_name> to its capability dir (and nothing stale).

Exit code: 0 when consistent, 1 with one line per problem otherwise. Stdlib-only (pyproject is
read with a minimal line parser — the checked tables hold only single-line `key = "value"` pairs).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_DIR = REPO_ROOT / "src" / "capabilities"
MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
PYPROJECT = REPO_ROOT / "pyproject.toml"
FRAMEWORK = REPO_ROOT / "src" / "mcp_framework.py"
PREFIX = "freeglm-"

errors: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail(f"{rel(path)}: unreadable or invalid JSON ({exc})")
        return None


def framework_version() -> str | None:
    m = re.search(r'^__version__ = "([^"]+)"', FRAMEWORK.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        fail(f"{rel(FRAMEWORK)}: __version__ not found")
        return None
    return m.group(1)


def parse_toml_table(text: str, table: str) -> dict[str, str]:
    """Minimal single-line `key = "value"` parser for one [table] of pyproject.toml."""
    out: dict[str, str] = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        if current == table and "=" in line:
            key, _, val = line.partition("=")
            out[key.strip().strip('"')] = val.strip().strip('"')
    return out


def server_package(cap_dir: Path) -> str | None:
    """The capability's MCP-server package dir (a valid import name with an __init__.py), if any."""
    for sub in sorted(cap_dir.iterdir()):
        if sub.is_dir() and sub.name.isidentifier() and (sub / "__init__.py").is_file():
            return sub.name
    return None


def entry_name_of(server_cfg: dict, expected: str, where: str) -> None:
    """Check one mcpServers entry: a uvx launch whose console entry (last arg) is the server key."""
    args = server_cfg.get("args")
    if not isinstance(args, list) or not args:
        fail(f"{where}: mcpServers entry has no args list")
        return
    if args[-1] != expected:
        fail(f"{where}: console entry is {args[-1]!r}, expected {expected!r}")


def check_mcp_servers(mcp_servers, expected_name: str, where: str) -> None:
    if not isinstance(mcp_servers, dict) or set(mcp_servers) != {expected_name}:
        keys = sorted(mcp_servers) if isinstance(mcp_servers, dict) else mcp_servers
        fail(f"{where}: mcpServers keys {keys!r}, expected exactly [{expected_name!r}]")
        return
    entry_name_of(mcp_servers[expected_name], expected_name, f"{where} → {expected_name}")


def check_capability(cap_dir: Path, version: str | None, scripts: dict[str, str], package_dir: dict[str, str]) -> None:
    cap = cap_dir.name
    expected_name = PREFIX + cap
    import_name = server_package(cap_dir)

    manifests = {
        "claude": cap_dir / ".claude-plugin" / "plugin.json",
        "codex": cap_dir / ".codex-plugin" / "plugin.json",
        "qoder": cap_dir / ".qoder-plugin" / "plugin.json",
        "zcode": cap_dir / ".zcode-plugin" / "plugin.json",
    }
    mcp_json_path = cap_dir / ".mcp.json"
    loaded: dict[str, dict] = {}
    for kind, path in manifests.items():
        if not path.is_file():
            fail(f"{rel(cap_dir)}: missing {path.relative_to(cap_dir)}")
            continue
        data = load_json(path)
        if data is None:
            continue
        loaded[kind] = data
        if data.get("name") != expected_name:
            fail(f"{rel(path)}: name {data.get('name')!r}, expected {expected_name!r}")
        if version is not None and data.get("version") != version:
            fail(f"{rel(path)}: version {data.get('version')!r} != mcp_framework __version__ {version!r}")

    if import_name is not None:
        # MCP-server capability: server key + entry consistent everywhere, and registered in pyproject.
        if "claude" in loaded:
            check_mcp_servers(loaded["claude"].get("mcpServers"), expected_name, f"{rel(manifests['claude'])}")
        if not mcp_json_path.is_file():
            fail(f"{rel(cap_dir)}: server capability without .mcp.json (codex/qoder manifests need it)")
        else:
            mcp_json = load_json(mcp_json_path)
            if mcp_json is not None:
                check_mcp_servers(mcp_json.get("mcpServers"), expected_name, rel(mcp_json_path))
        if "codex" in loaded and loaded["codex"].get("mcpServers") != "./.mcp.json":
            fail(f"{rel(manifests['codex'])}: mcpServers should reference './.mcp.json'")
        if "qoder" in loaded and loaded["qoder"].get("mcp") != ".mcp.json":
            fail(f"{rel(manifests['qoder'])}: mcp should reference '.mcp.json'")
        if scripts.get(expected_name) != f"{import_name}.__main__:main":
            fail(
                f"pyproject.toml [project.scripts]: {expected_name} = {scripts.get(expected_name)!r}, "
                f"expected '{import_name}.__main__:main'"
            )
        expected_pkg_dir = f"src/capabilities/{cap}/{import_name}"
        if package_dir.get(import_name) != expected_pkg_dir:
            fail(
                f"pyproject.toml [tool.setuptools.package-dir]: {import_name} = "
                f"{package_dir.get(import_name)!r}, expected {expected_pkg_dir!r}"
            )
    else:
        # Skill-only capability: must not declare an MCP server anywhere.
        if "claude" in loaded and "mcpServers" in loaded["claude"]:
            fail(f"{rel(manifests['claude'])}: skill-only capability declares mcpServers")
        if expected_name in scripts:
            fail(f"pyproject.toml [project.scripts]: {expected_name} registered but {cap} has no server package")


def main() -> int:
    version = framework_version()
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    scripts = parse_toml_table(pyproject_text, "project.scripts")
    package_dir = parse_toml_table(pyproject_text, "tool.setuptools.package-dir")
    caps = sorted(d for d in CAPABILITIES_DIR.iterdir() if d.is_dir())

    # Marketplace ↔ capability dirs. The canonical marketplace is .claude-plugin/marketplace.json;
    # the zcode copy is generated from it and must stay in sync (same plugins/owner).
    zcode_marketplace = REPO_ROOT / ".zcode-plugin" / "marketplace.json"
    zcode_mp = load_json(zcode_marketplace) if zcode_marketplace.is_file() else None
    marketplace = load_json(MARKETPLACE)
    listed: set[str] = set()
    if marketplace is not None:
        meta_version = marketplace.get("metadata", {}).get("version")
        if version is not None and meta_version != version:
            fail(f"{rel(MARKETPLACE)}: metadata.version {meta_version!r} != mcp_framework __version__ {version!r}")
        names = [p.get("name") for p in marketplace.get("plugins", [])]
        for name in {n for n in names if names.count(n) > 1}:
            fail(f"{rel(MARKETPLACE)}: duplicate plugin name {name!r}")
        for plugin in marketplace.get("plugins", []):
            name, source = plugin.get("name"), plugin.get("source", "")
            src_dir = (REPO_ROOT / source).resolve()
            cap = src_dir.name
            listed.add(cap)
            if name != PREFIX + cap:
                fail(f"{rel(MARKETPLACE)}: plugin {name!r} does not match source dir name ({PREFIX}{cap!s})")
            if not src_dir.is_dir():
                fail(f"{rel(MARKETPLACE)}: {name}: source {source!r} does not exist")
            elif not (src_dir / ".claude-plugin" / "plugin.json").is_file():
                fail(f"{rel(MARKETPLACE)}: {name}: source has no .claude-plugin/plugin.json")
        if zcode_mp is not None:
            znames = [p.get("name") for p in zcode_mp.get("plugins", [])]
            if znames != names:
                fail(
                    f"{rel(zcode_marketplace)}: plugins {znames!r} != canonical {names!r} "
                    f"(keep the zcode copy in sync)"
                )
            if zcode_mp.get("owner", {}).get("name") != marketplace.get("owner", {}).get("name"):
                fail(f"{rel(zcode_marketplace)}: owner.name differs from {rel(MARKETPLACE)}")

    # Per-capability manifests ↔ pyproject.
    for cap_dir in caps:
        check_capability(cap_dir, version, scripts, package_dir)
        if cap_dir.name not in listed:
            notes.append(f"note: {rel(cap_dir)} is not listed in {rel(MARKETPLACE)} (intentional for the template)")

    # Reverse direction: nothing stale in pyproject.
    cap_names = {d.name for d in caps}
    for entry in scripts:
        if not entry.startswith(PREFIX) or entry[len(PREFIX) :] not in cap_names:
            fail(f"pyproject.toml [project.scripts]: {entry!r} has no capability dir under src/capabilities/")
    for import_name, target in package_dir.items():
        if import_name.startswith("freeglm") and not (REPO_ROOT / target).is_dir():
            fail(f"pyproject.toml [tool.setuptools.package-dir]: {import_name} -> {target!r} does not exist")

    for note in notes:
        print(note)
    if errors:
        print(f"\nFAIL — {len(errors)} inconsistency(ies):", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1
    print(f"OK — {len(caps)} capabilities consistent across marketplace.json, plugin manifests and pyproject.toml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
