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
import queue
import subprocess
import sys
import threading

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

    The initialize response is awaited before sending ``notifications/initialized`` and
    ``tools/list``. Closing stdin immediately after a pre-written batch races the SDK's async
    reader on fast Linux runners: EOF can cancel the queued list request after initialize. A
    tiny reader thread gives the raw client a cross-platform timeout without relying on
    ``select()`` (which cannot wait on subprocess pipes on Windows).
    """
    proc = subprocess.Popen(
        [sys.executable, CORE_SERVER_DIR],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=dict(os.environ),
    )
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    stdout_queue: queue.Queue[str | None] = queue.Queue()

    def _pump_stdout() -> None:
        for line in proc.stdout:
            stdout_lines.append(line)
            stdout_queue.put(line)
        stdout_queue.put(None)

    def _pump_stderr() -> None:
        stderr_lines.extend(proc.stderr)

    stdout_thread = threading.Thread(target=_pump_stdout, daemon=True)
    stderr_thread = threading.Thread(target=_pump_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    responses: dict[int, dict] = {}

    def _send(payload: str) -> None:
        proc.stdin.write(payload)
        proc.stdin.flush()

    def _wait_for(response_id: int) -> None:
        while response_id not in responses:
            try:
                line = stdout_queue.get(timeout=120)
            except queue.Empty as exc:
                raise AssertionError(
                    f"timed out waiting for JSON-RPC id={response_id}; stderr tail: {''.join(stderr_lines)[-500:]}"
                ) from exc
            if line is None:
                raise AssertionError(
                    f"server exited before JSON-RPC id={response_id}; stderr tail: {''.join(stderr_lines)[-500:]}"
                )
            msg = json.loads(line.strip())
            if "id" in msg:
                responses[msg["id"]] = msg

    try:
        _send(
            _rpc(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-stdio-test", "version": "0"},
                },
                id_=1,
            )
        )
        _wait_for(1)
        _send(_rpc("notifications/initialized") + _rpc("tools/list", {}, id_=2))
        _wait_for(2)
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        stdout_thread.join(timeout=10)
        stderr_thread.join(timeout=10)

    # Validate every line, not only the two responses consumed while synchronizing.
    for raw in stdout_lines:
        if raw.strip():
            json.loads(raw)
    assert responses, f"no JSON-RPC responses on stdout; stderr tail: {''.join(stderr_lines)[-500:]}"
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
