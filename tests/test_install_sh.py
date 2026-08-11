"""Regression checks for the installer's non-interactive helper functions."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _bash(script: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "NO_COLOR": "1", **env_overrides}
    return subprocess.run(
        ["bash", "-c", f"source ./install.sh --help >/dev/null; {script}"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_run_cmd_propagates_command_failure():
    result = _bash('QMP_DRY=0; run_cmd false >/dev/null 2>&1; test "$?" -eq 1')
    assert result.returncode == 0, result.stderr


def test_cap_spec_uses_file_url_for_local_checkout(tmp_path):
    checkout = tmp_path / "checkout with spaces"
    checkout.mkdir()
    result = _bash("REPO_URL=$TEST_REPO; cap_spec core", TEST_REPO=str(checkout))
    assert result.returncode == 0, result.stderr
    assert result.stdout == f"freeglm[core] @ file://{str(checkout).replace(' ', '%20')}"
