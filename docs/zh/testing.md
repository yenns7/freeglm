# 测试

[English](../en/testing.md) · **中文**

`uv run --with pytest --extra all pytest -m "not reachability" tests/` 会在隔离环境中统一运行完整离线套件。

对于新插件，不需要显式安装， `conftest.py` 把 `src/` 和各 `src/capabilities/<cap>/` 加进 `sys.path` 并自动发现所有 server 包，`import freeglm_<yourname>` 即可, fixtures(`sample_image` / `sample_video`)也能复用。

## 现有测试

- `test_tools.py` —— 测试core server：in-process 调 `handle()`(工具发现 / schema / read_image / read_video / budget / 时间戳回归)+ 用 MCP SDK 的 stdio client 走完整 initialize → tools/list → tools/call。
- `test_mcp_framework.py` —— 共享框架：`tool_schema` / `build_registry` 的 schema 变换与工具发现。
- `test_api_clients.py` —— 共享网络层(`shared.api_openai` / `api_dashscope` / `retry`)。
- `test_api_tools.py` —— Mock Provider 调用的云端工具 schema/handler；覆盖 GLM / DashScope 路由与媒体格式回归。
- `test_api_reachability.py` —— 智谱 GLM、DashScope、Serper 的显式 opt-in、凭据门控在线检查；普通离线套件会跳过。
- `test_security_contract.py` —— 凭据、脱敏、私有配置、公开 schema 及安装器/运行时一致性回归。
- `test_video_memory.py` —— 测试video memory server：没建 graph_memory.json 时返回 isError。
- `test_build_merge.py` —— video-memory 构建：`build_graph.merge_chunks`。
- `test_video_edit.py` —— video-edit测试：只测 schema/handler。
- `test_example.py` —— example 能力的示例工具：只测 schema/handler。
- `test_blender.py` / `test_freecad.py` —— thin-client 能力(blender / freecad)：schema/handler 表面、无 app 监听时优雅降级、MCP stdio 桥。
- `test_launch_autoinstall.py` —— blender/freecad `--launch-app` 背后的免 root app 自动下载与失败诊断(hermetic;下载/解压环节 monkeypatch)。
- `test_renderers.py` / `test_visualize_real.py` —— `visualize()` 渲染测试。
- `test_repo_sync.py` —— video-memory build 副本一致性；version一致性 `mcp_framework.__version__`。

## 新插件要写哪几层

按插件「产出什么」逐层加,最少写第 1 层:

**1. Smoke test(必写)** `tests/test_<yourname>.py`。本地工具照 `test_example.py`,远程 / 需外部服务的照 `test_video_edit.py`(只测表面,不 live 调用):

```python
import freeglm_<yourname> as m

def test_lists_tools():
    assert {t["name"] for t in m.list_tools()} == {"tool_a", "tool_b"}

def test_handler():
    assert m.get_handler("tool_a")({"arg": "x"})[0]["type"] == "text"   # 或 image
```

**2. 渲染素材(工具产出图 / 文本时)** —— 小素材进 `tests/assets/` + 参数化(照 `test_renderers.py`),大素材进 `tests/assets/real/`(照 `test_visualize_real.py`);缺依赖 skip 不 fail。

**3. 协议层(server 有 stdio 行为时)** —— 用 conftest 的 `mcp_call()` 把 server 当子进程拉起走真实 MCP client(参考 `test_video_memory.py`)。

**4. 防漂移守卫** —— 在 `test_repo_sync.py` 加 byte-identical 断言(参考 video-memory 的 build 副本)。

## 跑

```bash
uv run --with pytest --extra all pytest -m "not reachability" tests/  # 完整离线套件
uv run --with pytest --extra all pytest tests/test_<yourname>.py -v
uvx ruff format --check path/to/changed.py && uvx ruff check .        # 提交前
```

## Provider 在线连通性

在线测试与离线套件有意分离。它们会把生成的非敏感 fixture 发给真实服务，可能消耗额度或产生费用。
先通过 `bash install.sh configure` 配置 Key，不要把 Key 值写进命令。测试同时要求对应凭据与显式
`FREEGLM_RUN_REACHABILITY=1` 开关：

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k zhipu tests/test_api_reachability.py
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k dashscope tests/test_api_reachability.py
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra search pytest -m reachability -k serper tests/test_api_reachability.py
```

测试被跳过不能作为 Provider 已通过的证据。账号配置、结果解释和排障见
[Provider 与 API 配置指南](provider-setup.md)。

## 速查

- [ ] `tests/test_<yourname>.py` smoke —— 本地参考 `test_example.py`,远程参考 `test_video_edit.py`
- [ ] 有渲染 / 产出 → 素材进 `tests/assets/`(小)或 `real/`(大)+ 参数化
- [ ] server 有协议行为 → `mcp_call` 端到端,参考 `test_video_memory.py`
- [ ] 刻意重复文件 → `test_repo_sync.py` 加guard
- [ ] 完整离线套件通过；相关且已明确授权的在线连通性测试通过；Ruff 干净
