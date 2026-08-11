# Provider 与 API 配置指南

[English](../en/provider-setup.md) · **中文**

本页说明如何安全接入智谱 GLM、阿里云百炼 DashScope、Serper，以及如何判断“配置存在”与“真实功能可用”。如果你说的“GIM API”是项目中的视觉后端，这里的正确名称是 **GLM API**。

## 先选最小能力

| 目标 | 安装能力 | Provider / 配置 |
|---|---|---|
| 本地读图、读视频、看文档 | `freeglm-core` | 无 API Key |
| VQA、OCR、grounding | `freeglm-api` | 智谱 GLM 或 DashScope，二选一即可 |
| Omni 音视频、专用 ASR、生成、video-memory 构建 | 对应 `api` / `video-edit` / `video-memory` | DashScope；GLM Key 不能代替 |
| 网页搜索、网页抽取、反查图 | `freeglm-search` | Serper |
| SAM3 分割 / 自建 ASR | `freeglm-api` | 自建服务 URL |

从第一性原理看，接入只需要四件事：安装工具、让运行进程拿到凭据、明确把数据发给哪个 Provider、用一个真实小请求验收。不要把“配置文件里有一行”误当成“端点、Key、模型和网络都可用”。

## 凭据安全规则

- 不要把 Key 粘到聊天、Agent prompt、MCP 参数、源码、截图或命令行参数中。
- 不要运行会打印 Key 的命令，也不要把真实 Key 写进 `.env` 后提交。
- 推荐运行 `bash install.sh configure`。安装器用隐藏输入写入 `~/.freeglm/config`，文件权限为 `0600`；环境变量仍有更高优先级。
- `--check-system` 和 `bash install.sh verify` 只报告 `set` / `not set` 与来源，不显示 Key 片段。
- 怀疑泄漏时，在 Provider 控制台撤销旧 Key、创建新 Key，再更新本机配置；只改本地文件不能让已泄漏的 Key 失效。

## 智谱 GLM：最短接入路径

智谱官方流程是登录开放平台、创建 API Key，并使用通用 OpenAI 兼容端点 `https://open.bigmodel.cn/api/paas/v4/`。FreeGLM 默认模型是 `glm-4.6v-flash`。请以[智谱 HTTP API 指南](https://docs.bigmodel.cn/cn/guide/develop/http/introduction)和 [GLM-4.6V-Flash 模型文档](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.6v-flash)为准。

1. 安装 `freeglm-api`，或在仓库中运行引导式安装器。
2. 运行 `bash install.sh configure`。
3. 进入 **Credentials & endpoints**，选择 `ZHIPU_API_KEY`，在隐藏输入框中粘贴 Key。
4. 通常保留 `ZHIPU_BASE_URL` 默认值，并保留 `ZHIPU_VISION_MODEL=glm-4.6v-flash`。只有代理服务或组织网关明确要求时才改端点，而且端点与凭据必须属于同一受信任服务。
5. 返回主菜单运行 **Verify**，选择 `freeglm-api`。

也可以在源码目录做无网络检查：

```bash
python3 scripts/check_security_contract.py
uvx --from ".[api]" freeglm-api --check-system
```

`vision_chat`、`ocr`、`grounding` 都支持 `provider="zhipu"`。只配置 `ZHIPU_API_KEY` 时会自动选智谱；如果 DashScope Key 也存在，自动路由默认选 DashScope，因此希望固定使用 GLM 时应显式选 `provider="zhipu"`。

视频规则：可公开访问的远程视频 URL 走 GLM 原生 `video_url`；本地视频在配置 OSS 后先上传为签名 URL，否则在本机抽帧后按图片输入。`dry_run=true` 永不上传。私有媒体会离开本机时，应先确认用户已经同意发送到智谱或所配置的 OSS。

### 智谱真实连通性验收

在线测试会生成一张小测试图并真实调用 API，可能消耗免费额度或产生费用；它不会输出 Key。明确同意使用该账号后运行：

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k zhipu tests/test_api_reachability.py
```

在 Agent 中再做三项人工验收：

```text
对这张测试图片做一句话描述，并明确使用 provider=zhipu。
识别这张测试图片中的文字，并明确使用 provider=zhipu。
找出这张测试图片中的彩色区域，返回框坐标，并明确使用 provider=zhipu。
```

## DashScope：视觉与更多媒体能力

在[阿里云百炼控制台创建 API Key](https://help.aliyun.com/zh/model-studio/get-api-key/)。Key、Base URL、地域和计费方式必须匹配；跨地域混用通常表现为 401。端点选择以[百炼 Base URL 文档](https://help.aliyun.com/en/model-studio/base-url)和[地域说明](https://help.aliyun.com/zh/model-studio/regions/)为准。

运行 `bash install.sh configure`，在 **Credentials & endpoints** 中填写 `DASHSCOPE_API_KEY`。仅在所选地域需要时调整 `DASHSCOPE_BASE_URL`。然后运行：

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k dashscope tests/test_api_reachability.py
```

GLM 目前只接管 `vision_chat` / `ocr` / `grounding`；`transcribe_audio`、Omni、生成和 video-memory 构建仍按各自文档使用 DashScope 或自建服务。

## Serper：搜索能力

在 [Serper](https://serper.dev/) 控制台创建 Key，再通过 `bash install.sh configure` 填写 `SERPER_API_KEY`。验收：

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra search pytest -m reachability -k serper tests/test_api_reachability.py
```

`web_search` 与 `web_extractor` 会把查询或 URL 发给外部服务。反查本地图片还会先上传到文档声明的第三方公开图床，因此必须在每次上传前取得明确同意；机密图片不应走该流程。

## 分层校验：从“装上”到“能用”

| 层级 | 校验什么 | 推荐方法 |
|---|---|---|
| 配置 | 所需变量存在、来源可识别且值不泄漏 | `bash install.sh verify` 或 `<entry> --check-system` |
| 发现 | Skill 与 MCP server 在当前 Agent 中真实启用 | 查看实时 skill/tool 清单，确认目标工具名 |
| 离线契约 | schema、路由、脱敏、媒体 fallback、MCP 协议 | `uv run --with pytest --extra all pytest -m "not reachability" tests/` |
| 在线连通 | Key、端点、模型、网络和账号额度 | 本页的 opt-in reachability 测试 |
| 业务验收 | 真实任务的质量、隐私、成本满足预期 | 用最小非敏感样例执行一次 Agent 任务 |

在线测试默认跳过，即使机器上已有 Key，也必须设置 `FREEGLM_RUN_REACHABILITY=1` 才会发请求。

## 常见故障

| 现象 | 优先检查 |
|---|---|
| `no API key` | 变量名是否正确；运行进程是否能读 `~/.freeglm/config`；环境中的空值是否遮蔽文件配置 |
| 401 / 鉴权失败 | Key 是否被撤销；Base URL、地域、计费计划是否匹配；是否把一个 Provider 的 Key 发给另一个端点 |
| 404 / model not found | 模型名是否对当前账号开放；先恢复默认 `glm-4.6v-flash` 或 Provider 官方模型名 |
| 429 | 额度、并发或速率限制；降低并发并按 Provider 控制台确认配额 |
| 请求超时 | 网络、媒体体积和 `FREEGLM_CHAT_TIMEOUT`；先用小图片排除账号问题 |
| 明明配了 GLM 却走 DashScope | 两个 Key 同时存在时 `auto` 默认 DashScope；显式设置 `provider="zhipu"` |
| Agent 看不到工具 | Skill/MCP 未安装到当前 harness，或安装后未重启/刷新工具清单 |
| 本地视频失败 | 检查 `ffmpeg` / `ffprobe`；若要原生视频 URL，完整配置 OSS 或传 Provider 可访问的 URL |

智谱的 HTTP 状态与业务码可查[官方错误码说明](https://docs.bigmodel.cn/cn/faq/api-code)。日志和错误文本应经过脱敏；不要为了排障打印请求头、签名 URL 或配置文件内容。

## 轮换或删除 Key

1. 先在 Provider 控制台创建新 Key或撤销旧 Key。
2. 运行 `bash install.sh configure`，选择对应字段；输入 `-` 会清除本机配置。
3. 若环境变量中也设置过旧 Key，同时在启动 Agent 的可信 secret store 中更新或删除。
4. 重启 Agent/MCP server，再执行一次配置检查和最小在线验收。

## 维护者：新增 Provider 或模型

新增接入时逐项完成，不能只加一个环境变量：

1. 在 `src/shared/env.py` 的 `CONFIG_FIELDS` 与 `install.sh` 的 `CONFIG_SPEC` 同步登记字段，并正确标记 secret。
2. 在共享 resolver 中实现显式 Provider 选择和安全默认值。公开 MCP schema 只能暴露 `provider` 等非敏感选择，不能暴露 `api_key`、`base_url`、token 或 secret。
3. 确认图片、视频、音频的真实 wire format；未知能力应保守 fallback，不能根据旧印象声称 Provider 不支持。
4. 更新工具描述、Agent 路由、数据出境说明和本页教程。
5. 添加离线单元测试，以及由凭据和显式开关双重门控的 reachability 测试。
6. 若增加新能力或入口，同步清单并运行 `python3 scripts/check_manifests.py`。完整目录流程见[新增能力指南](how_to_add_new_capability.md)。
7. 合并前运行安全契约、完整离线测试、Ruff 和 `git diff --check`；禁止在测试 fixture 或示例中放真实 Key。
