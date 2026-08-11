"""Smoke + protocol tests for the blender capability's MCP server.

conftest auto-discovers freeglm_blender (it scans src/capabilities/*/ for the
server package), so it imports like any other server. The server is a THIN CLIENT: its
handlers connect over a socket to a running Blender + blender-mcp addon. There is no live
Blender in CI, so we exercise:

  1. discovery + the advertised schema/handler surface (surface smoke, per test_example.py)
  2. graceful degradation — every handler must return an informative text block (not crash)
     when no Blender is listening (mirrors test_video_memory's "no memory configured" path)
  3. the MCP stdio bridge end-to-end (initialize -> tools/list -> tools/call)

Live modeling (real execute_blender_code / screenshots) needs a running Blender under
xvfb with the vendored addon; that is Phase C, done manually per the skill.
"""

import json
import os
import socket
import threading
import time

from conftest import REPO_ROOT, mcp_call

import freeglm_blender as m

BLENDER_SERVER_DIR = os.path.join(REPO_ROOT, "src", "capabilities", "blender", "freeglm_blender")

# The full trained tool surface (blender-mcp), ported 1:1. Doubles as a drift guard.
BLENDER_TOOLS = {
    "execute_blender_code",
    "get_viewport_screenshot",
    "get_scene_info",
    "get_object_info",
    "get_polyhaven_status",
    "get_polyhaven_categories",
    "search_polyhaven_assets",
    "download_polyhaven_asset",
    "set_texture",
    "get_sketchfab_status",
    "search_sketchfab_models",
    "get_sketchfab_model_preview",
    "download_sketchfab_model",
    "get_hyper3d_status",
    "generate_hyper3d_model_via_text",
    "generate_hyper3d_model_via_images",
    "poll_rodin_job_status",
    "import_generated_asset",
    "get_hunyuan3d_status",
    "generate_hunyuan3d_model",
    "poll_hunyuan_job_status",
    "import_generated_asset_hunyuan",
}

# Point the loader at a port nothing is listening on, so every test takes the
# "no live Blender" path deterministically (default is localhost:9876).
_ENV = {**os.environ, "BLENDER_HOST": "127.0.0.1", "BLENDER_PORT": "59999"}


# ── surface (in-process) ─────────────────────────────────────────────


def test_lists_the_full_trained_surface():
    assert {t["name"] for t in m.list_tools()} == BLENDER_TOOLS


def test_every_tool_has_schema_and_handler():
    for tool in m.list_tools():
        assert tool["inputSchema"]["type"] == "object"
        assert callable(m.get_handler(tool["name"]))


def test_unknown_tool_has_no_handler():
    assert m.get_handler("does_not_exist") is None


# ── graceful degradation (no live Blender) ───────────────────────────


def test_execute_code_degrades_gracefully(monkeypatch):
    # The workhorse tool must return a helpful text block, not raise, when Blender is down.
    monkeypatch.setenv("BLENDER_HOST", "127.0.0.1")
    monkeypatch.setenv("BLENDER_PORT", "59999")
    # Reset the cached connection singleton so it re-reads the env.
    import freeglm_blender.loader as loader

    loader._connection = None
    content = m.get_handler("execute_blender_code")({"code": "print(1)"})
    assert content and content[0]["type"] == "text"
    assert "connect" in content[0]["text"].lower() or "blender" in content[0]["text"].lower()


# ── protocol (real MCP client over stdio) ────────────────────────────


def test_server_tools_list_matches_in_process():
    result = mcp_call(BLENDER_SERVER_DIR, lambda s: s.list_tools(), env=_ENV)
    assert {t.name for t in result.tools} == {t["name"] for t in m.list_tools()}


def test_server_execute_code_call_degrades():
    # Over the wire, a down Blender yields a text block (handler catches and returns),
    # not a transport crash.
    result = mcp_call(
        BLENDER_SERVER_DIR,
        lambda s: s.call_tool("execute_blender_code", {"code": "print(1)"}),
        env=_ENV,
    )
    assert any(getattr(b, "type", None) == "text" for b in result.content)


# ── regression: connection lifecycle + input validation (blcad review fixes) ──


class _MockBlender:
    """Minimal stand-in for a running Blender + addon: reads one JSON command and writes one
    JSON {"status","result"} back over a persistent socket, recording the command types seen.
    A small per-command delay widens the interleaving window for the concurrency test."""

    def __init__(self, delay: float = 0.02):
        self.delay = delay
        self.requests: list[str] = []
        self._rlock = threading.Lock()
        self._running = True
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(("127.0.0.1", 0))
        self._srv.listen(8)
        self.port = self._srv.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while self._running:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        buf = b""
        while self._running:
            try:
                chunk = conn.recv(8192)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            try:
                cmd = json.loads(buf.decode())
            except json.JSONDecodeError:
                continue
            buf = b""
            with self._rlock:
                self.requests.append(cmd["type"])
            if self.delay:
                time.sleep(self.delay)
            resp = {"status": "success", "result": {"echo": cmd["type"], "enabled": True}}
            try:
                conn.sendall(json.dumps(resp).encode())
            except OSError:
                break

    def close(self):
        self._running = False
        try:
            self._srv.close()
        except OSError:
            pass


def test_get_connection_does_not_ping_per_call(monkeypatch):
    """A steady-state tool call must issue exactly one request — no extra get_polyhaven_status
    ping doubling the round-trips (blcad review, finding 6)."""
    srv = _MockBlender(delay=0)
    monkeypatch.setenv("BLENDER_HOST", "127.0.0.1")
    monkeypatch.setenv("BLENDER_PORT", str(srv.port))
    import freeglm_blender.loader as loader

    loader._connection = None
    try:
        loader.get_connection().send_command("get_scene_info")  # warm up (establishes conn)
        srv.requests.clear()
        loader.get_connection().send_command("get_object_info")  # steady state
        assert srv.requests == ["get_object_info"]
    finally:
        srv.close()
        loader._connection = None


def test_concurrent_calls_do_not_race_on_socket(monkeypatch):
    """Concurrent send_command calls (framework worker threads) must not interleave on the single
    shared socket and misroute responses (blcad review, finding 3)."""
    srv = _MockBlender(delay=0.02)
    monkeypatch.setenv("BLENDER_HOST", "127.0.0.1")
    monkeypatch.setenv("BLENDER_PORT", str(srv.port))
    import freeglm_blender.loader as loader

    loader._connection = None
    try:
        conn = loader.get_connection()
        results: dict[str, str] = {}
        errors: list[str] = []

        def call(i):
            tag = f"cmd{i}"
            try:
                results[tag] = conn.send_command(tag).get("echo")
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))

        threads = [threading.Thread(target=call, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)
        assert not errors, errors
        assert all(results.get(f"cmd{i}") == f"cmd{i}" for i in range(8)), results
    finally:
        srv.close()
        loader._connection = None


def test_hyper3d_url_validation_rejects_garbage():
    """The image-URL guard must reject non-URLs; plain urlparse() is truthy for any string
    (blcad review, finding 4)."""
    from freeglm_blender.tools.generate_hyper3d_model_via_images import _valid_url

    assert _valid_url("https://example.com/a.png")
    assert _valid_url("http://example.com/a.png")
    assert not _valid_url("not a url")
    assert not _valid_url("")
    assert not _valid_url(None)
    out = m.get_handler("generate_hyper3d_model_via_images")({"input_image_urls": ["not a url", ""]})
    assert out[0]["type"] == "text" and "valid" in out[0]["text"].lower()


def test_launch_app_status_goes_to_stderr_not_stdout(capsys):
    """launch_app is reused on the in-server autolaunch path, where stdout is the MCP JSON-RPC
    channel — its status text must go to stderr (blcad review, finding 1)."""
    from freeglm_blender import _launch

    busy = socket.socket()
    busy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    busy.bind(("127.0.0.1", 0))
    busy.listen(1)
    port = busy.getsockname()[1]
    try:
        rc = _launch.launch_app(["--port", str(port)])  # "already listening" branch
    finally:
        busy.close()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert "already listening" in captured.err
