"""Example tool (ENV / config): report how this capability resolves its configuration.

Demonstrates shared.env.get_env — precedence: environment > ~/.freeglm/config > default.
It reads a demo tunable (FREEGLM_EXAMPLE_GREETING) and reports whether DASHSCOPE_API_KEY resolves
(WITHOUT printing the secret) plus where the shared config file lives.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from shared.content import text
from shared.env import config_file, get_env

_DEFAULT_GREETING = "hello from the example capability"


class ConfigProbeArgs(BaseModel):
    """No arguments — reports the capability's resolved configuration."""


TOOL: dict[str, Any] = {
    "name": "config_probe",
    "description": (
        "Report resolved configuration via shared.env.get_env "
        "(precedence: environment > ~/.freeglm/config > default). "
        "Demonstrates reading env/config from an MCP tool without leaking secrets."
    ),
    "args": ConfigProbeArgs,
}


def handle(arguments: dict[str, Any]) -> list[dict[str, Any]]:
    greeting = get_env("FREEGLM_EXAMPLE_GREETING", _DEFAULT_GREETING)
    has_key = bool(get_env("DASHSCOPE_API_KEY"))
    lines = [
        f"config file (read when a var isn't in the environment): {config_file()}",
        f"FREEGLM_EXAMPLE_GREETING resolves to: {greeting}",
        f"DASHSCOPE_API_KEY: {'set' if has_key else 'not set'}",
        "",
        "Precedence: environment variable > ~/.freeglm/config > default.",
        "Override the greeting via env (export FREEGLM_EXAMPLE_GREETING=hi) "
        "or the config file (FREEGLM_EXAMPLE_GREETING=hi).",
    ]
    return [text("\n".join(lines))]
