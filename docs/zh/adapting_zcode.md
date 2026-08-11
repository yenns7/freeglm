# 将 FreeGLM 适配到 ZCode(以及任何 Claude 兼容 harness)

FreeGLM 以**插件市场(marketplace)**的形式发布,ZCode(以及 Claude Code、Qoder、Codex、OpenClaw 等)都能直接消费。本指南说明 ZCode 适配的原理、为什么复用 Claude marketplace 格式,以及如何为其它 harness 复刻同一套做法——这也是上游 Qwen-MM-Plugins 项目做多平台支持用的同一配方。

## 「适配」在这里指什么

FreeGLM 是 **harness 无关**的:每个能力 = 一个 `skill/`(让模型知道有这套工具)+ 一个可选的 MCP server 包(`<import_name>/`)。所谓「适配某个 harness」,只是那一层薄的注册文件,告诉 harness 这些东西在哪:

| Harness | 注册机制 | 关键文件 |
|---|---|---|
| ZCode | Claude 兼容插件市场 | `.zcode-plugin/marketplace.json` + 每能力 `.zcode-plugin/plugin.json` |
| Claude Code | Claude 插件市场 | `.claude-plugin/marketplace.json` + 每能力 `.claude-plugin/plugin.json` |
| Codex | Codex 插件市场 | `.codex-plugin/plugin.json` + `.mcp.json` |
| Qoder | Qoder 插件市场 | `.qoder-plugin/plugin.json` + `.mcp.json` |
| OpenClaw / Qwen Code / Gemini | 原生命令或市场 | 见 `docs/zh/installation.md` |

MCP server 在任何地方都从同一个不可变版本拉起 —— `uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.1" freeglm-<cap>` —— 所以适配新 harness **不需要改服务端代码，只需要改注册清单**。

## ZCode 适配是怎么接线的

### 1. 根级市场(`.zcode-plugin/marketplace.json`)

一份 Claude schema 的市场文件。ZCode 读它来列出 FreeGLM 的能力:

```json
{
  "name": "freeglm",
  "owner": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "metadata": {
    "description": "FreeGLM multimodal Agent Skills + MCP servers for local media I/O, cloud understanding, search, creation, and 3D/CAD workflows",
    "version": "1.0.1"
  },
  "plugins": [
    { "name": "freeglm-core", "source": "./src/capabilities/core", "description": "…" },
    { "name": "freeglm-api",  "source": "./src/capabilities/api",  "description": "…" }
  ]
}
```

> 规范市场文件在 `.claude-plugin/marketplace.json`；仓库内的 `.zcode-plugin/marketplace.json`
> 镜像其 metadata 和插件条目。CI 里的 `scripts/check_manifests.py` 会同时校验这份镜像、
> 每个平台清单、不可变发布 ref 和 `pyproject.toml`。

### 2. 每能力清单(`.zcode-plugin/plugin.json`)

每个能力目录各带一份。以带 MCP 的 `api` 为例:

```json
{
  "name": "freeglm-api",
  "version": "1.0.1",
  "description": "FreeGLM API — cloud media understanding by model family: VL vision chat, OCR, and grounding on DashScope Qwen or Zhipu GLM-4.6V-Flash; Omni A/V, ASR, and segmentation on DashScope.",
  "author": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "skills": "./skill",
  "mcpServers": {
    "freeglm-api": {
      "command": "uvx",
      "args": ["--from", "freeglm[api] @ git+https://github.com/yenns7/freeglm.git@v1.0.1", "freeglm-api"]
    }
  }
}
```

纯 skill 能力(`edu-agent`)省略 `mcpServers`,只注册 `skills`。

### 3. ZCode 实际装了什么

- **`skills`** —— 复制/注册,让模型知道有这套工具(里面的 `SKILL.md`)。
- **`mcpServers`** —— 一个 stdio MCP server,由 `uvx` 按需拉起。首次启动会从 `v1.0.1` git tag 解析
  `freeglm[<cap>]` 并把它的 Python extras 装进隔离缓存 —— 无需手动 pip。`blender` / `freecad`
  额外在 `env` 里传 `FREEGLM_AUTOLAUNCH=1`。

### 4. 在 ZCode 中安装

ZCode 不在 `PATH` 上提供插件 CLI。先打开一个 workspace，再进入 **Settings → Plugins →
Create → Add marketplace**，输入 `https://github.com/yenns7/freeglm.git`，在 Personal 区域找到
需要的 `freeglm-<cap>` 并点击 **Install**。发布新版本后，在 marketplace source 面板执行
**Refresh**。

## 为其它 harness 复刻

1. **有插件市场的 harness** —— 把市场 + 每能力清单复制进它要读的目录(`.codex-plugin/`、
   `.qoder-plugin/` …),加进根级 `marketplace.json`。整份适配就完成了。
2. **有原生命令但没市场的**(Qwen Code、Gemini CLI)—— `install.sh` 已自动化
   (`qwen extensions install …`、`gemini mcp add …`)。
3. **只能手改配置的**(opencode、pi、QwenPaw)—— 在 harness 自己的配置里注册 MCP server + skill,
   精确配置块见 `docs/zh/installation.md`。

> 上游项目的经验法则:**一个市场、每 harness 一份清单、加平台零代码改动**。

## Agent 路由策略

安装后请直接采用统一的 [Agent 接入与路由策略](agent-integration.md)，不要再维护一份
ZCode 专用 prompt。该策略要求检查实时 Skill/MCP 清单、按能力归属路由，禁止通过 prompt
或工具参数传递凭据，覆盖私有媒体上传同意，并且只有实时工具 schema 明确支持且存在具体
诊断需求时才使用 preview/`dry_run`。
