# Testing

**English** · [中文](../zh/testing.md)

`uv run --with pytest --extra all pytest -m "not reachability" tests/` runs the complete offline suite in an isolated environment.

New plugins need no explicit installation: `conftest.py` adds `src/` and each `src/capabilities/<cap>/` to `sys.path` and auto-discovers all server packages, so `import freeglm_<yourname>` just works, and the fixtures (`sample_image` / `sample_video`) can be reused too.

## Existing tests

- `test_tools.py` — tests the core server: calls `handle()` in-process (tool discovery / schema / read_image / read_video / budget / timestamp regression) plus a full initialize → tools/list → tools/call over the MCP SDK's stdio client.
- `test_mcp_framework.py` — the shared framework: `tool_schema` / `build_registry` schema transforms and tool discovery.
- `test_api_clients.py` — the shared network layer (`shared.api_openai` / `api_dashscope` / `retry`).
- `test_api_tools.py` — cloud-tool schemas and handlers with provider calls mocked; includes GLM / DashScope routing and media-format regressions.
- `test_api_reachability.py` — opt-in, credential-gated live checks for DashScope, Zhipu GLM, and Serper; skipped by the ordinary offline suite.
- `test_security_contract.py` — credential, redaction, private-config, public-schema, and installer/runtime consistency regressions.
- `test_video_memory.py` — tests the video-memory server: returns isError when no graph_memory.json has been built.
- `test_build_merge.py` — the video-memory build: `build_graph.merge_chunks`.
- `test_video_edit.py` — video-edit tests: schema/handler only.
- `test_example.py` — the example capability's demo tools: schema/handler only.
- `test_blender.py` / `test_freecad.py` — the thin-client capabilities (blender / freecad): schema/handler surface, graceful degradation when no app is listening, and the MCP stdio bridge.
- `test_launch_autoinstall.py` — the rootless app auto-download + failure diagnosis behind blender/freecad `--launch-app` (hermetic; download/extract seams monkeypatched).
- `test_renderers.py` / `test_visualize_real.py` — `visualize()` rendering tests.
- `test_repo_sync.py` — consistency of the video-memory build copies; version consistency of `mcp_framework.__version__`.

## Which layers a new plugin should write

Add layers according to what the plugin "produces", writing at least layer 1:

**1. Smoke test (required)** `tests/test_<yourname>.py`. For local tools follow `test_example.py`; for remote / external-service tools follow `test_video_edit.py` (surface only, no live calls):

```python
import freeglm_<yourname> as m

def test_lists_tools():
    assert {t["name"] for t in m.list_tools()} == {"tool_a", "tool_b"}

def test_handler():
    assert m.get_handler("tool_a")({"arg": "x"})[0]["type"] == "text"   # or image
```

**2. Rendering assets (when a tool produces images / text)** — small assets go in `tests/assets/` + parametrize (follow `test_renderers.py`); large assets go in `tests/assets/real/` (follow `test_visualize_real.py`); skip (don't fail) when dependencies are missing.

**3. Protocol layer (when the server has stdio behavior)** — use conftest's `mcp_call()` to launch the server as a subprocess and drive it through a real MCP client (see `test_video_memory.py`).

**4. Anti-drift guard** — add a byte-identical assertion in `test_repo_sync.py` (see the video-memory build copies).

## Running

```bash
uv run --with pytest --extra all pytest -m "not reachability" tests/  # complete offline suite
uv run --with pytest --extra all pytest tests/test_<yourname>.py -v
uvx ruff format --check path/to/changed.py && uvx ruff check .        # before committing
```

## Live provider reachability

Live tests are intentionally separate from the offline suite. They send generated, non-sensitive
fixtures to real services and can consume quota or incur cost. Configure keys through
`bash install.sh configure`; never place a key value in the command. The tests require both the
relevant credential and the explicit `FREEGLM_RUN_REACHABILITY=1` opt-in:

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k zhipu tests/test_api_reachability.py
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k dashscope tests/test_api_reachability.py
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra search pytest -m reachability -k serper tests/test_api_reachability.py
```

A skipped test is not evidence that the provider passed. See [provider and API setup](provider-setup.md)
for account setup, interpretation, and troubleshooting.

## Quick checklist

- [ ] `tests/test_<yourname>.py` smoke — local: see `test_example.py`; remote: see `test_video_edit.py`
- [ ] has rendering / output → assets in `tests/assets/` (small) or `real/` (large) + parametrize
- [ ] server has protocol behavior → `mcp_call` end-to-end, see `test_video_memory.py`
- [ ] intentionally duplicated files → add a guard in `test_repo_sync.py`
- [ ] complete offline suite green; relevant explicitly authorized reachability tests green; Ruff clean
