#!/usr/bin/env python3
"""Cross-check plugin manifests: marketplace.json ↔ per-capability manifests ↔ pyproject.toml.

For every capability under src/capabilities/<cap>/ this verifies the naming convention
(capability name / plugin name / MCP-server key / console entry are all `freeglm-<cap>`)
and that the three registration surfaces agree:

- .claude-plugin/marketplace.json — each plugin's name matches its source dir, the dir exists and
  carries a .claude-plugin/plugin.json; the marketplace metadata version matches mcp_framework.
- src/capabilities/<cap>/{.claude-plugin,.codex-plugin,.qoder-plugin,.zcode-plugin}/plugin.json
  (+ .mcp.json) — same name and version (== mcp_framework.__version__); every server launch is
  exactly `uvx --from freeglm[<cap>]@v<version> freeglm-<cap>` on the immutable release tag;
  Claude/ZCode inline MCP declarations equal the companion .mcp.json; skill-only capabilities
  declare no MCP server.
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
GIT_REPOSITORY = "https://github.com/yenns7/freeglm.git"

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


def check_server_config(server_cfg: dict, cap: str, expected: str, version: str | None, where: str) -> None:
    """Check one stdio server uses the exact immutable uvx release launch."""
    if not isinstance(server_cfg, dict):
        fail(f"{where}: server config is not an object")
        return
    if server_cfg.get("command") != "uvx":
        fail(f"{where}: command is {server_cfg.get('command')!r}, expected 'uvx'")
    args = server_cfg.get("args")
    if not isinstance(args, list) or not args:
        fail(f"{where}: mcpServers entry has no args list")
        return
    if any("@main" in arg for arg in args if isinstance(arg, str)):
        fail(f"{where}: mutable @main ref is forbidden; pin the release tag")
    if version is None:
        return
    expected_args = [
        "--from",
        f"freeglm[{cap}] @ git+{GIT_REPOSITORY}@v{version}",
        expected,
    ]
    if args != expected_args:
        fail(f"{where}: args {args!r}, expected immutable launch {expected_args!r}")


def check_mcp_servers(mcp_servers, cap: str, expected_name: str, version: str | None, where: str) -> None:
    if not isinstance(mcp_servers, dict) or set(mcp_servers) != {expected_name}:
        keys = sorted(mcp_servers) if isinstance(mcp_servers, dict) else mcp_servers
        fail(f"{where}: mcpServers keys {keys!r}, expected exactly [{expected_name!r}]")
        return
    check_server_config(mcp_servers[expected_name], cap, expected_name, version, f"{where} → {expected_name}")


def skill_paths(value) -> list[str] | None:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def check_capability(
    cap_dir: Path,
    version: str | None,
    scripts: dict[str, str],
    package_dir: dict[str, str],
    marketplace_owner: str | None,
) -> None:
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
        paths = skill_paths(data.get("skills"))
        if paths != ["./skill"]:
            fail(f"{rel(path)}: skills {data.get('skills')!r}, expected './skill'")

    skill_file = cap_dir / "skill" / "SKILL.md"
    if not skill_file.is_file():
        fail(f"{rel(cap_dir)}: manifests declare './skill' but {rel(skill_file)} is missing")
    if "claude" in loaded and "zcode" in loaded:
        if loaded["zcode"].get("description") != loaded["claude"].get("description"):
            fail(f"{rel(manifests['zcode'])}: description differs from Claude canonical manifest")
        if marketplace_owner is not None:
            author = loaded["zcode"].get("author")
            author_name = author.get("name") if isinstance(author, dict) else None
            if author_name != marketplace_owner:
                fail(f"{rel(manifests['zcode'])}: author.name differs from marketplace owner {marketplace_owner!r}")

    if import_name is not None:
        # MCP-server capability: server key + entry consistent everywhere, and registered in pyproject.
        if "claude" in loaded:
            check_mcp_servers(
                loaded["claude"].get("mcpServers"), cap, expected_name, version, rel(manifests["claude"])
            )
        if "zcode" in loaded:
            check_mcp_servers(
                loaded["zcode"].get("mcpServers"), cap, expected_name, version, rel(manifests["zcode"])
            )
        if not mcp_json_path.is_file():
            fail(f"{rel(cap_dir)}: server capability without .mcp.json (codex/qoder manifests need it)")
        else:
            mcp_json = load_json(mcp_json_path)
            if mcp_json is not None:
                companion_servers = mcp_json.get("mcpServers")
                check_mcp_servers(companion_servers, cap, expected_name, version, rel(mcp_json_path))
                for kind in ("claude", "zcode"):
                    if kind in loaded and loaded[kind].get("mcpServers") != companion_servers:
                        fail(f"{rel(manifests[kind])}: inline mcpServers differs from {rel(mcp_json_path)}")
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
        for kind, data in loaded.items():
            if "mcpServers" in data or "mcp" in data:
                fail(f"{rel(manifests[kind])}: skill-only capability declares an MCP server")
        if mcp_json_path.exists():
            fail(f"{rel(mcp_json_path)}: skill-only capability must not ship an MCP manifest")
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
    marketplace_owner: str | None = None
    if marketplace is not None:
        owner = marketplace.get("owner")
        marketplace_owner = owner.get("name") if isinstance(owner, dict) else None
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
            for field in ("owner", "metadata", "plugins"):
                if zcode_mp.get(field) != marketplace.get(field):
                    fail(f"{rel(zcode_marketplace)}: {field} differs from canonical {rel(MARKETPLACE)}")

    # Per-capability manifests ↔ pyproject.
    for cap_dir in caps:
        check_capability(cap_dir, version, scripts, package_dir, marketplace_owner)
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
