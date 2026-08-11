"""Lightweight end-to-end stdio test for the core server (P3.6b).

Incremental to test_tools.py's protocol tests: those drive the server through the MCP
SDK's *client* (ClientSession). Here the client side is raw newline-delimited JSON-RPC
written straight to the subprocess's stdin — the same way a harness config launches it
(`python3 src/capabilities/core/freeglm_core`) — so a framing/handshake regression
that the SDK client would paper over still gets caught. Asserts the full handshake
(initialize → initialized → tools/list) and that every advertised tool's wire metadata is
complete (name / description / normalized inputSchema).

The *server* needs the `mcp` SDK to run, so this skips when it's absent.
"""

import json
import os
import subprocess
import sys

import pytest
from conftest import CORE_SERVER_DIR

pytest.importorskip("mcp")  # the server subprocess can't start without the SDK

pytestmark = pytest.mark.skipif(not CORE_SERVER_DIR, reason="freeglm_core server package not found")


def _rpc(method: str, params: dict | None = None, id_: int | None = None) -> str:
    msg: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if id_ is not None:
        msg["id"] = id_
    return json.dumps(msg) + "\n"


@pytest.fixture(scope="module")
def rpc_responses() -> dict[int, dict]:
    """Run one full handshake + tools/list against a fresh server subprocess.

    All requests are written up front and stdin closed; the stdio server processes them
    in order and exits on EOF. Returns the responses keyed by request id.
    """
    wire = (
        _rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "e2e-stdio-test", "version": "0"},
            },
            id_=1,
        )
        + _rpc("notifications/initialized")
        + _rpc("tools/list", {}, id_=2)
    )
    proc = subprocess.run(
        [sys.executable, CORE_SERVER_DIR],
        input=wire.encode(),
        capture_output=True,
        timeout=120,
        env=dict(os.environ),
    )
    responses = {}
    for line in proc.stdout.decode().splitlines():
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)  # every stdout line must be valid JSON-RPC (nothing else may leak)
        if "id" in msg:
            responses[msg["id"]] = msg
    assert responses, f"no JSON-RPC responses on stdout; stderr tail: {proc.stderr.decode()[-500:]}"
    return responses


def test_initialize_handshake(rpc_responses):
    init = rpc_responses.get(1)
    assert init and "result" in init, f"initialize failed: {init}"
    result = init["result"]
    assert result.get("protocolVersion")
    assert result.get("serverInfo", {}).get("name")


def test_tools_list_complete_schemas(rpc_responses):
    listed = rpc_responses.get(2)
    assert listed and "result" in listed, f"tools/list failed: {listed}"
    tools = listed["result"]["tools"]
    assert len(tools) > 0

    names = set()
    for tool in tools:
        assert tool.get("name"), f"tool without a name: {tool}"
        names.add(tool["name"])
        assert tool.get("description", "").strip(), f"{tool['name']}: empty description"
        schema = tool.get("inputSchema")
        assert isinstance(schema, dict) and schema.get("type") == "object", f"{tool['name']}: bad inputSchema"
        assert isinstance(schema.get("properties"), dict), f"{tool['name']}: inputSchema must list properties"
        # tool_schema() normalization: no auto-titles, no unresolved $refs on the wire
        blob = json.dumps(schema)
        assert "$ref" not in blob, f"{tool['name']}: inputSchema leaked an unresolved $ref"
    assert len(names) == len(tools), "tool names must be unique"
    # spot-check one stable core tool made it through with its real argument
    read_image = next(t for t in tools if t["name"] == "read_image")
    assert "image_path" in read_image["inputSchema"]["properties"]
