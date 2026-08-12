#!/usr/bin/env python3
"""Static, stdlib-only security contract checks for FreeGLM.

This intentionally avoids importing capability packages: it must run in a fresh checkout before
third-party dependencies are installed. Findings identify only a file, line, and rule; matched
credential values are never printed.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SECRET_ENV_NAMES = (
    "DASHSCOPE_API_KEY",
    "ZHIPU_API_KEY",
    "SERPER_API_KEY",
    "OSS_AK",
    "OSS_SK",
)
_UNSAFE_EXAMPLE_PATTERNS = (
    (re.compile(r"--api-key(?=\s|=|[`'\"]|$)", re.IGNORECASE), "credential command-line flag"),
    (re.compile(r"--set\s+(?:<[^>]+>\s+)?KEY=VALUE", re.IGNORECASE), "generic KEY=VALUE command example"),
    (
        re.compile(
            rf"(?:\bexport\s+)?\b(?:{'|'.join(_SECRET_ENV_NAMES)})\s*=\s*[^\s`]+",
            re.IGNORECASE,
        ),
        "credential value assignment example",
    ),
)


def _constant_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _assigned_value(statement: ast.stmt, name: str) -> ast.AST | None:
    if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in statement.targets):
        return statement.value
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and statement.target.id == name:
        return statement.value
    return None


def _tool_arg_models(tree: ast.Module) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for statement in tree.body:
        value = _assigned_value(statement, "TOOL")
        if not isinstance(value, ast.Dict):
            continue
        for key, item in zip(value.keys, value.values):
            if _constant_string(key) == "args" and isinstance(item, ast.Name):
                out.append((item.id, item.lineno))
    return out


def _field_names(model: ast.ClassDef, classes: dict[str, ast.ClassDef]) -> list[tuple[str, int]]:
    """Return declared names and constant Pydantic aliases, including local base classes."""
    out: list[tuple[str, int]] = []
    for base in model.bases:
        if isinstance(base, ast.Name) and base.id in classes:
            out.extend(_field_names(classes[base.id], classes))
    for statement in model.body:
        if not isinstance(statement, ast.AnnAssign) or not isinstance(statement.target, ast.Name):
            continue
        out.append((statement.target.id, statement.lineno))
        value = statement.value
        if not isinstance(value, ast.Call):
            continue
        for keyword in value.keywords:
            if keyword.arg in {"alias", "serialization_alias", "validation_alias"}:
                alias = _constant_string(keyword.value)
                if alias:
                    out.append((alias, keyword.value.lineno))
    return out


def _credential_property(name: str) -> bool:
    normalized = name.strip().lower().replace("-", "_")
    return (
        normalized in {"api_key", "apikey", "base_url", "baseurl", "token", "secret"}
        or normalized.endswith("_api_key")
        or normalized.endswith("_access_token")
        or normalized.endswith("_auth_token")
        or normalized.endswith("_secret")
        or normalized.endswith("_secret_key")
    )


def check_public_mcp_schemas(root: Path = ROOT) -> list[str]:
    """Reject credential and endpoint override properties in every statically declared TOOL."""
    findings: list[str] = []
    tool_count = 0
    capability_root = root / "src" / "capabilities"
    for path in sorted(capability_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            findings.append(f"{path.relative_to(root)}:1: cannot inspect Python source ({type(exc).__name__})")
            continue
        arg_models = _tool_arg_models(tree)
        if not arg_models:
            continue
        tool_count += len(arg_models)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        for model_name, line in arg_models:
            model = classes.get(model_name)
            if model is None:
                findings.append(
                    f"{path.relative_to(root)}:{line}: TOOL args model {model_name!r} is not locally inspectable"
                )
                continue
            for field, field_line in _field_names(model, classes):
                if _credential_property(field):
                    findings.append(
                        f"{path.relative_to(root)}:{field_line}: public MCP property {field!r} "
                        "may expose credentials or endpoint overrides"
                    )
    if tool_count == 0:
        findings.append("src/capabilities:1: no public TOOL schemas found; static discovery contract may be stale")
    return findings


def _public_guidance_files(root: Path) -> Iterable[Path]:
    seen: set[Path] = set()
    candidates = [*root.glob("README*.md"), *(root / "docs").rglob("*.md")]
    candidates.extend((root / "src" / "capabilities").glob("**/skill/**/*.md"))
    candidates.append(root / "src" / "mcp_framework.py")
    for path in sorted(candidates):
        if path.is_file() and path not in seen:
            seen.add(path)
            yield path


def check_credential_examples(root: Path = ROOT) -> list[str]:
    """Reject examples that put a credential in argv, shell history, or copy/paste text."""
    findings: list[str] = []
    for path in _public_guidance_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            findings.append(f"{path.relative_to(root)}:1: cannot inspect guidance ({type(exc).__name__})")
            continue
        for line_number, line in enumerate(lines, 1):
            for pattern, rule in _UNSAFE_EXAMPLE_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path.relative_to(root)}:{line_number}: unsafe {rule}")
    return findings


def _config_field_entries(tree: ast.Module) -> list[ast.Tuple]:
    for statement in tree.body:
        value = _assigned_value(statement, "CONFIG_FIELDS")
        if isinstance(value, (ast.List, ast.Tuple)):
            return [item for item in value.elts if isinstance(item, ast.Tuple)]
    return []


def _python_config_catalog(tree: ast.Module) -> dict[str, tuple[bool, int]]:
    catalog: dict[str, tuple[bool, int]] = {}
    for item in _config_field_entries(tree):
        if len(item.elts) < 2:
            continue
        key = _constant_string(item.elts[0])
        secret_node = item.elts[1]
        if key and isinstance(secret_node, ast.Constant) and isinstance(secret_node.value, bool):
            catalog[key] = (secret_node.value, item.lineno)
    return catalog


def _installer_config_catalog(source: str) -> tuple[dict[str, tuple[bool, int]], list[str]]:
    catalog: dict[str, tuple[bool, int]] = {}
    findings: list[str] = []
    in_spec = False
    row = re.compile(r'^\s*"([A-Z][A-Z0-9_]*)\|([01])\|')
    for line_number, line in enumerate(source.splitlines(), 1):
        if not in_spec:
            in_spec = line.strip() == "CONFIG_SPEC=("
            continue
        if line.strip() == ")":
            break
        match = row.match(line)
        if not match:
            continue
        key, secret = match.groups()
        if key in catalog:
            findings.append(f"install.sh:{line_number}: duplicate CONFIG_SPEC key {key!r}")
        catalog[key] = (secret == "1", line_number)
    return catalog, findings


def check_config_catalog_sync(root: Path = ROOT) -> list[str]:
    """Keep installer and runtime config catalogs aligned on key names and secret handling."""
    env_path = root / "src" / "shared" / "env.py"
    install_path = root / "install.sh"
    try:
        env_tree = ast.parse(env_path.read_text(encoding="utf-8"), filename=str(env_path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [f"src/shared/env.py:1: cannot inspect CONFIG_FIELDS ({type(exc).__name__})"]
    try:
        install_source = install_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"install.sh:1: cannot inspect CONFIG_SPEC ({type(exc).__name__})"]

    python_catalog = _python_config_catalog(env_tree)
    installer_catalog, findings = _installer_config_catalog(install_source)
    if not python_catalog:
        findings.append("src/shared/env.py:1: CONFIG_FIELDS key/secret catalog is not statically inspectable")
    if not installer_catalog:
        findings.append("install.sh:1: CONFIG_SPEC key/secret catalog is not statically inspectable")

    for key in sorted(python_catalog.keys() - installer_catalog.keys()):
        findings.append(
            f"src/shared/env.py:{python_catalog[key][1]}: config key {key!r} is missing from install.sh CONFIG_SPEC"
        )
    for key in sorted(installer_catalog.keys() - python_catalog.keys()):
        findings.append(
            f"install.sh:{installer_catalog[key][1]}: config key {key!r} is missing from shared.env CONFIG_FIELDS"
        )
    for key in sorted(python_catalog.keys() & installer_catalog.keys()):
        if python_catalog[key][0] != installer_catalog[key][0]:
            findings.append(
                f"install.sh:{installer_catalog[key][1]}: config key {key!r} has a different "
                "secret flag than shared.env"
            )
    return findings


def check_config_storage(root: Path = ROOT) -> list[str]:
    """Keep local secret files ignored, secret defaults empty, and config reads/writes protected."""
    findings: list[str] = []
    ignore_path = root / ".gitignore"
    try:
        ignore_lines = {line.strip() for line in ignore_path.read_text(encoding="utf-8").splitlines()}
    except OSError:
        ignore_lines = set()
    for required in {".env", ".env.*", "!.env.example", ".freeglm/"}:
        if required not in ignore_lines:
            findings.append(f".gitignore:1: missing local credential ignore rule {required!r}")

    env_path = root / "src" / "shared" / "env.py"
    try:
        source = env_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(env_path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return findings + [f"src/shared/env.py:1: cannot inspect config storage ({type(exc).__name__})"]

    required_storage_guards = {
        "os.fstat(f.fileno())": "config read must inspect the opened descriptor's permissions",
        "mode & 0o077": "config read must detect group/other access",
        "os.chmod(tmp, 0o600)": "config write must set owner-only permissions",
        "os.replace(tmp, path)": "config write must replace atomically",
    }
    for snippet, rule in required_storage_guards.items():
        if snippet not in source:
            findings.append(f"src/shared/env.py:1: {rule}")

    entries = _config_field_entries(tree)
    if not entries:
        findings.append("src/shared/env.py:1: CONFIG_FIELDS catalog is not statically inspectable")
    for item in entries:
        if len(item.elts) < 4:
            continue
        key = _constant_string(item.elts[0])
        secret = isinstance(item.elts[1], ast.Constant) and item.elts[1].value is True
        default = _constant_string(item.elts[3])
        if secret and default:
            findings.append(
                f"src/shared/env.py:{item.lineno}: secret config field {key or '<unknown>'!r} has a non-empty default"
            )
    return findings


def run_checks(root: Path = ROOT) -> list[str]:
    return [
        *check_public_mcp_schemas(root),
        *check_credential_examples(root),
        *check_config_storage(root),
        *check_config_catalog_sync(root),
    ]


def main() -> int:
    findings = run_checks()
    if findings:
        print("security contract violations:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1
    print("security contract: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
