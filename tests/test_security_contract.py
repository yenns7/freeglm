"""Regression coverage for credential boundaries and sanitized diagnostics."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pytest
from scripts import check_security_contract as security_contract

import mcp_framework
from shared import api_openai, env, retry
from shared.content import text_error


def test_checked_in_public_tool_schemas_have_no_credential_fields(repo_root):
    assert security_contract.check_public_mcp_schemas(Path(repo_root)) == []


def test_schema_check_rejects_a_credential_alias(tmp_path):
    tool = tmp_path / "src" / "capabilities" / "demo" / "tool.py"
    tool.parent.mkdir(parents=True)
    tool.write_text(
        """from pydantic import BaseModel, Field
class Args(BaseModel):
    max_tokens: int = 10
    endpoint: str = Field(alias="api_key")
TOOL = {"name": "demo", "args": Args}
""",
        encoding="utf-8",
    )

    findings = security_contract.check_public_mcp_schemas(tmp_path)

    assert len(findings) == 1
    assert "public MCP property 'api_key'" in findings[0]


def test_guidance_check_rejects_credential_argv_and_assignments(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "unsafe.md").write_text(
        "Run client --api-key example-secret\n"
        "For automation use tool --set KEY=VALUE\n"
        "export DASHSCOPE_API_KEY=example-secret\n",
        encoding="utf-8",
    )

    findings = security_contract.check_credential_examples(tmp_path)

    assert len(findings) == 3
    assert all("example-secret" not in finding for finding in findings)


def test_checked_in_runtime_and_installer_config_catalogs_match(repo_root):
    assert security_contract.check_config_catalog_sync(Path(repo_root)) == []


def test_config_catalog_check_detects_missing_extra_and_secret_drift(tmp_path):
    env_source = tmp_path / "src" / "shared" / "env.py"
    env_source.parent.mkdir(parents=True)
    env_source.write_text(
        "CONFIG_FIELDS = [\n"
        "    ('API_KEY', True, 'Credentials', '', 'credential'),\n"
        "    ('TIMEOUT', False, 'Limits', '30', 'seconds'),\n"
        "]\n",
        encoding="utf-8",
    )
    (tmp_path / "install.sh").write_text(
        'CONFIG_SPEC=(\n'
        '  "API_KEY|0|cred||credential"\n'
        '  "EXTRA|0|dirs||extra"\n'
        ')\n',
        encoding="utf-8",
    )

    findings = security_contract.check_config_catalog_sync(tmp_path)

    assert len(findings) == 3
    assert any("'TIMEOUT' is missing from install.sh" in finding for finding in findings)
    assert any("'EXTRA' is missing from shared.env" in finding for finding in findings)
    assert any("'API_KEY' has a different secret flag" in finding for finding in findings)


def test_redaction_covers_final_tool_error_and_retry_log(monkeypatch, caplog):
    raw = (
        "POST https://storage.example/video?Signature=query-sentinel "
        "DASHSCOPE_API_KEY=dash-sentinel Authorization: Bearer bearer-sentinel "
        "token=token-sentinel sk-0123456789abcdef"
    )

    sanitized = retry.redact_sensitive_error(raw)
    final = text_error(raw)[0]["text"]

    secrets = (
        "query-sentinel",
        "dash-sentinel",
        "bearer-sentinel",
        "token-sentinel",
        "sk-0123456789abcdef",
    )
    for secret in secrets:
        assert secret not in sanitized
        assert secret not in final

    monkeypatch.setattr(retry.time, "sleep", lambda _seconds: None)
    caplog.set_level(logging.WARNING, logger="security-contract-test")
    logger = logging.getLogger("security-contract-test")

    def fail():
        raise RuntimeError(raw)

    assert retry.retry_call(fail, attempts=2, on_exhausted="none", log=logger) is None
    logged = caplog.text
    for secret in secrets:
        assert secret not in logged


def test_explicit_endpoint_never_inherits_environment_credentials(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dash-env-sentinel")
    monkeypatch.setenv("ZHIPU_API_KEY", "zhipu-env-sentinel")

    for provider in (None, "auto", "dashscope", "zhipu"):
        url, key = api_openai.resolve_openai_endpoint(
            {"base_url": "https://untrusted.example/v1"}, provider=provider
        )
        assert url == "https://untrusted.example/v1"
        assert key == "EMPTY"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are not meaningful on Windows")
def test_config_read_warns_on_broad_permissions_without_printing_values(tmp_path, monkeypatch, capsys):
    config = tmp_path / "config"
    config.write_text("DASHSCOPE_API_KEY=config-sentinel\n", encoding="utf-8")
    config.chmod(0o644)
    monkeypatch.setenv("FREEGLM_CONFIG", str(config))
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setattr(env, "_config_cache", None)

    assert env.get_env("DASHSCOPE_API_KEY") == "config-sentinel"
    warning = capsys.readouterr().err
    assert "mode 0644" in warning
    assert "chmod 600" in warning
    assert "config-sentinel" not in warning


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are not meaningful on Windows")
def test_config_write_is_owner_only(tmp_path, monkeypatch):
    config = tmp_path / "config"
    monkeypatch.setenv("FREEGLM_CONFIG", str(config))
    monkeypatch.setattr(env, "_config_cache", None)

    env.set_config({"DASHSCOPE_API_KEY": "config-sentinel"})

    assert config.stat().st_mode & 0o777 == 0o600


def test_cli_refuses_secret_values_in_process_arguments(tmp_path, monkeypatch, capsys):
    config = tmp_path / "config"
    monkeypatch.setenv("FREEGLM_CONFIG", str(config))
    monkeypatch.setattr(env, "_config_cache", None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["freeglm-example", "--set", "DASHSCOPE_API_KEY=argv-sentinel"],
    )

    with pytest.raises(SystemExit) as exc:
        mcp_framework.run_main("freeglm_example")

    assert exc.value.code == 2
    output = capsys.readouterr()
    assert "argv-sentinel" not in output.out + output.err
    assert not config.exists()


def test_config_report_lists_all_credentials_without_fragments(tmp_path, monkeypatch):
    dash_key = "dashprefix-secret-dashsuffix"
    zhipu_key = "zhipuprefix-secret-zhipusuffix"
    config = tmp_path / "config"
    config.write_text(f"ZHIPU_API_KEY={zhipu_key}\n", encoding="utf-8")
    config.chmod(0o600)
    monkeypatch.setenv("FREEGLM_CONFIG", str(config))
    monkeypatch.setenv("DASHSCOPE_API_KEY", dash_key)
    for key in ("ZHIPU_API_KEY", "SERPER_API_KEY", "OSS_AK", "OSS_SK"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(env, "_config_cache", None)

    report = mcp_framework.config_report("freeglm-example")

    assert "DASHSCOPE_API_KEY (environment): set" in report
    assert "ZHIPU_API_KEY (config file): set" in report
    assert "SERPER_API_KEY: not set" in report
    assert "OSS_AK: not set" in report
    assert "OSS_SK: not set" in report
    for fragment in (dash_key, zhipu_key, "dashprefix", "dashsuffix", "zhipuprefix", "zhipusuffix"):
        assert fragment not in report
