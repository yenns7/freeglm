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

MCP server 在任何地方都用同一条命令拉起 —— `uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@main" freeglm-<cap>` —— 所以适配新 harness **永远不需要改代码,只需要改清单**。

## ZCode 适配是怎么接线的

### 1. 根级市场(`.zcode-plugin/marketplace.json`)

一份 Claude schema 的市场文件。ZCode 读它来列出 FreeGLM 的能力:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "freeglm",
  "description": "FreeGLM multimodal capabilities for ZCode — derived from Qwen-MM-Plugins with a Zhipu GLM-4.6V-Flash vision backend",
  "owner": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "plugins": [
    { "name": "freeglm-core", "description": "…", "author": { "name": "yenns7" }, "source": "./src/capabilities/core" },
    { "name": "freeglm-api",  "description": "…", "author": { "name": "yenns7" }, "source": "./src/capabilities/api" }
  ]
}
```

> 规范市场文件在 `.claude-plugin/marketplace.json`;`.zcode-plugin/marketplace.json` 由它生成(同一 schema)。
> CI 里的 `scripts/check_manifests.py` 会保证每份平台清单与 `pyproject.toml` 同步。

### 2. 每能力清单(`.zcode-plugin/plugin.json`)

每个能力目录各带一份。以带 MCP 的 `api` 为例:

```json
{
  "name": "freeglm-api",
  "version": "1.0.0",
  "description": "FreeGLM api — cloud APIs for understanding media: VL (vision_chat / ocr / grounding), Omni A/V, ASR, segmentation (SAM3), exposed as an MCP server.",
  "author": { "name": "yenns7", "url": "https://github.com/yenns7/freeglm" },
  "skills": "./skill",
  "mcpServers": {
    "freeglm-api": {
      "command": "uvx",
      "args": ["--from", "freeglm[api] @ git+https://github.com/yenns7/freeglm.git@main", "freeglm-api"]
    }
  }
}
```

纯 skill 能力(`edu-agent`)省略 `mcpServers`,只注册 `skills`。

### 3. ZCode 实际装了什么

- **`skills`** —— 复制/注册,让模型知道有这套工具(里面的 `SKILL.md`)。
- **`mcpServers`** —— 一个 stdio MCP server,由 `uvx` 按需拉起。首次启动会从 git URL 解析
  `freeglm[<cap>]` 并把它的 Python extras 装进隔离缓存 —— 无需手动 pip。`blender` / `freecad`
  额外在 `env` 里传 `FREEGLM_AUTOLAUNCH=1`。

## 为其它 harness 复刻

1. **有插件市场的 harness** —— 把市场 + 每能力清单复制进它要读的目录(`.codex-plugin/`、
   `.qoder-plugin/` …),加进根级 `marketplace.json`。整份适配就完成了。
2. **有原生命令但没市场的**(Qwen Code、Gemini CLI)—— `install.sh` 已自动化
   (`qwen extensions install …`、`gemini mcp add …`)。
3. **只能手改配置的**(opencode、pi、QwenPaw)—— 在 harness 自己的配置里注册 MCP server + skill,
   精确配置块见 `docs/zh/installation.md`。

> 上游项目的经验法则:**一个市场、每 harness 一份清单、加平台零代码改动**。

## ZCode 快速接入提示词

装好 `freeglm-*` 能力后,把下面这段粘给 ZCode 里的 agent,让它强制走工具处理媒体(而不是
内置 OCR),并正确选择 VL 后端:

```text
你有 FreeGLM 的 MCP 工具可用。规则如下:
1. 要读、要 OCR、要描述、要框选任何图片 / 视频,必须调用 freeglm-* 的 MCP 工具
   (vision_chat / ocr / grounding)。绝不要退回 harness 自带的内置图像 / OCR 能力。
2. VL 工具两个后端,自动选择:只设了 ZHIPU_API_KEY 时默认智谱 GLM-4.6V-Flash
   (模型 glm-4.6v-flash,端点 open.bigmodel.cn);否则 DashScope Qwen(模型 qwen3.7-plus)。
   想强制指定,调用时传 provider="zhipu" 或 provider="dashscope"。
3. 智谱没有视频模态 —— 视频会在本地采样成一帧帧图片;video_max_frames 给到约视频秒数(~1fps)。
4. Omni 音视频、ASR、分割、生成、搜索分别需要 DASHSCOPE_API_KEY / SERPER_API_KEY。
5. 每个工作流先用一次 dry_run=true 预览请求 payload。
```

(中文版同时收录在 `README.zh.md` → 给 Agent 的快速接入提示词。)
