# 安装（详细）

快速路径 —— 插件市场与引导式安装 —— 在 [README](../../README.zh.md#-安装)。本页覆盖**不支持插件直装的 harness**（手动 skill + MCP 安装）、由此产生的工具名前缀、完整依赖参考，以及目录结构。

## Windows（WSL2）

Windows x64 用户推荐安装 Ubuntu WSL2，并在 WSL home 目录中 clone 仓库（例如
`~/code`），不要放在 `/mnt/c` 这类 Windows 挂载盘下。然后按照 Linux/macOS 的
相同命令安装。在管理员 PowerShell 中运行：

```powershell
wsl --install -d Ubuntu
```

使用 Windows 版 Codex 时，请将 agent 环境设为 WSL2，重启 Codex，并在该 WSL
环境中安装和使用插件。当前 Windows 仅支持 WSL2；原生 Windows 尚未完成验证。

## 非市场 harness：直接注册 skill + MCP

没有插件市场的 harness 需要在各自的配置里注册 **skill** 和 **MCP server**。**Qwen Code** 和 **Gemini CLI** 已被[引导式安装器](../../README.zh.md#-安装)自动化（`bash install.sh` → 选对应 harness）；其余（opencode、pi、QwenPaw 等）为手动 —— 见下方各 harness 步骤。其它 harness 最省事的办法是**让 agent 帮你装**（「装一下 `freeglm-<cap>`」）。

自动化安装器公开支持 `FREEGLM_REPO`、`FREEGLM_REF`、`FREEGLM_NO_TUI` 和
`FREEGLM_SPIN_TIMEOUT`；旧的 `QMP_*` 名称继续作为兼容别名。远端默认固定到不可变的
`v1.0.2` tag。

每个能力都是 `freeglm-<cap>`、uvx extras 为 `[<cap>]`；下面每个块里把 `<cap>` 换成具体能力名（`core` / `api` / `search` / `video-memory` / `video-edit` / `blender` / `freecad`）。

Claude Code 也可以走手动安装 —— 和插件市场的区别只在工具名：插件市场装的带 plugin 前缀 + server key（就是能力自己的名字，例如 `freeglm-<cap>`），手动 `mcp add` 用你自定义的 server name。以某个能力的 `read_image` 为例：

- 插件市场：`mcp__plugin_freeglm-<cap>_freeglm-<cap>__read_image`
- 手动：`mcp__freeglm-<cap>__read_image`

### skill link + mcp add（Claude Code 及同类）

```bash
# 1) skill
ln -s "$(pwd)/src/capabilities/<cap>/skill" ~/.claude/skills/freeglm-<cap>
# 2) MCP（本地代码把 --from 换成 "$(pwd)[<cap>]"）
claude mcp add freeglm-<cap> -- \
  uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.2" freeglm-<cap>
```

换能力时，把 skill 路径、`[<cap>]` profile、入口名 `freeglm-<cap>` 一起换成对应能力的。

### opencode

`npm i -g opencode-ai`，然后在 `~/.config/opencode/opencode.json`（或项目级 `opencode.json`）的 `mcp` 下注册 MCP server，并把 skill 放进 `~/.config/opencode/skills/`：

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "freeglm-<cap>": {
      "type": "local",
      "command": ["uvx", "--from", "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.2", "freeglm-<cap>"],
      "enabled": true
    }
  }
}
```

不要在这里注入 API key 占位符。子进程会继承真实存在的变量，FreeGLM 也会自行读取私有的
`~/.freeglm/config`；未设置变量若被展开为空串，反而会遮蔽配置文件中的有效值。

```bash
cp -r src/capabilities/<cap>/skill ~/.config/opencode/skills/freeglm-<cap>   # opencode 也会读 ~/.claude/skills/
```

无头运行：`opencode run "…"`。（自定义 OpenAI 兼容 provider 必须用 `modalities` 把模型标为可读图，否则 opencode 会丢掉返回的图片。）

### Qwen Code

`npm i -g @qwen-code/qwen-code@latest`。把一个能力作为**原生 extension** 安装（打包 skill + MCP + context），一条命令、走 git 从 Claude 市场拉：

```bash
qwen extensions install https://github.com/yenns7/freeglm.git:freeglm-<cap> --consent
```

或只注册 MCP server（再把 skill 拷进 `~/.qwen/skills/freeglm-<cap>`）：

```bash
qwen mcp add freeglm-<cap> --scope user --trust --timeout 600000 \
  uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.2" freeglm-<cap>
```

无头运行：`qwen -p "…" --yolo -o text`。卸载：`qwen extensions uninstall freeglm-<cap>`。

### Gemini CLI

`npm i -g @google/gemini-cli`。注册 MCP server + 安装 skill：

```bash
gemini mcp add -s user freeglm-<cap> \
  uvx --from "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.2" freeglm-<cap>
gemini skills install https://github.com/yenns7/freeglm.git --path src/capabilities/<cap>/skill --consent
```

能力目录不是独立 Gemini extension（有意不带 `gemini-extension.json`），所以远端和本地安装都应使用上面两条原生命令，不要运行 `gemini extensions link`。MCP 只在**受信任目录**下加载（提示时信任该目录即可）。无头运行：`gemini -p "…" -y`。卸载：`gemini mcp remove -s user freeglm-<cap>` + `gemini skills uninstall freeglm-<cap>`。

> Gemini CLI 只对接 **Google Gemini API** —— 不支持外部 / OpenAI 兼容的模型 provider。

### pi (earendil-works)

`npm i -g @earendil-works/pi-coding-agent`。pi 有**原生 skills**，但**没有内置 MCP**（设计如此）—— MCP 工具通过社区扩展 `pi-mcp-adapter` 提供：

```bash
cp -r src/capabilities/<cap>/skill ~/.pi/agent/skills/freeglm-<cap>   # skill（原生）
pi install npm:pi-mcp-adapter                                               # 一次性，用于 MCP
```

`~/.config/mcp/mcp.json`（`mcpServers` schema 与我们的 `.mcp.json` 相同）：

```json
{
  "settings": { "toolPrefix": "none" },
  "mcpServers": { "freeglm-<cap>": {
    "command": "uvx",
    "args": ["--from", "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.2", "freeglm-<cap>"]
  } }
}
```

不要写通用 `directTools` 列表：每个能力的工具名不同。server 会继承进程里真实存在的环境变量，并自行读取 `~/.freeglm/config`；省略 `env` 还能避免未设置变量被展开为空串后遮蔽配置文件中的有效 key。纯 skill 能力（edu-agent）只拷 skill 即可用。无头运行：`pi -p "…"`。

### QwenPaw 2.0

QwenPaw 2.0 本身不支持插件市场，所以只能手动安装。把 `<agent_id>` 换成当前 Agent/workspace id（默认 Agent 为 `default`），把 `<cap>` 换成能力名：

```bash
# 1) skill
cp -r src/capabilities/<cap>/skill ~/.qwenpaw/workspaces/<agent_id>/skills/freeglm-<cap>
qwenpaw skills list      # 触发 reconcile，登记进 manifest（此时 disabled）
qwenpaw skills config    # 交互勾选启用
# 2) MCP：写进 ~/.qwenpaw/workspaces/<agent_id>/agent.json 的 mcp.clients（无 CLI，改文件即可，有热加载）
```

```json
{
  "mcp": {
    "clients": {
      "freeglm-<cap>": {
        "name": "freeglm-<cap>",
        "enabled": true,
        "transport": "stdio",
        "command": "uvx",
        "args": ["--from", "freeglm[<cap>] @ git+https://github.com/yenns7/freeglm.git@v1.0.2", "freeglm-<cap>"]
      }
    }
  }
}
```

### ZCode

ZCode 是 Claude 兼容的插件市场型 harness，不在 `PATH` 上提供插件 CLI。请在已经打开的
workspace 中按真实 UI 操作：进入 **Settings → Plugins**，点击 **Create → Add marketplace**，
输入 `https://github.com/yenns7/freeglm.git`；然后在 Personal marketplace 中找到
`freeglm-<cap>` 并点击 **Install**。发布新版本后，通过 marketplace source 面板的
**Refresh** 操作刷新。

仓库开箱即支持 zcode：

- 根级 `.zcode-plugin/marketplace.json`（Claude schema 市场，`owner` = `yenns7`），以及
- 每个能力的 `.zcode-plugin/plugin.json`（`name` / `skills` / `mcpServers`，`author` = `yenns7`）。

每个插件的 `mcpServers` 通过 `uvx --from "freeglm[<cap>] @ git+…" freeglm-<cap>` 按需拉起
（无需手动 pip），`skills` 指向 `./skill`。默认先装 `core`（本地 I/O 基座）再按需装其他；
原理与如何为其它 harness 复刻这套适配，见 [ZCode 适配指南](adapting_zcode.md)。

## 依赖

`uvx` 首次启动时按 profile 把 Python 依赖装进隔离缓存。需要手动准备的只有两类。

### API Key（仅 API 工具需要）

VL 工具（`vision_chat` / `ocr` / `grounding`）需要 `DASHSCOPE_API_KEY` **或** `ZHIPU_API_KEY` —— 只设智谱 key 时 VL 工具会自动路由到 GLM-4.6V-Flash 后端（零 DashScope 配置）。`transcribe_audio` 与生成类工具仍需 `DASHSCOPE_API_KEY`。key 从 shell 环境继承（或写进 `~/.freeglm/config`）。联网工具（`web_search` / `web_extractor` / `image_search`）走 Serper API，需要 `SERPER_API_KEY`。原生读图 / 视频 / 文档不需要 key。账号创建、隐藏输入配置、在线验收、轮换和排障见 [Provider 与 API 配置指南](provider-setup.md)。

### 系统工具（需用系统包管理器手动装）

| 工具 | 供哪些功能 | 安装 |
|------|-----------|------|
| **ffmpeg** | `read_video` / `transcribe_audio` / video-memory / video-edit | `apt install ffmpeg`  ·  `brew install ffmpeg` |
| **libreoffice** | `visualize` 的 Office / DrawIO | `apt install libreoffice`  ·  `brew install --cask libreoffice` |
| **blender** | `visualize` 的 3D 高质量渲染（可选，默认回退 matplotlib） | `apt install blender`  ·  `brew install --cask blender` |
| **texlive**（pdflatex） | `visualize` 的 LaTeX | `apt install texlive-latex-base texlive-latex-extra` |
| **chromium**（playwright） | `visualize` 的网页截图 | `playwright install chromium` |

如何查看缺少的系统工具：

- 用 uvx 查看：`uvx --from "freeglm[all] @ git+https://github.com/yenns7/freeglm.git@v1.0.2" freeglm-<cap> --check-system`。
- server 启动时，若某个已装 extra 缺对应系统工具，会在 stderr 打印一行告警。
- 实际工具调用时，返回「请安装 X」的文字提示，其它工具照常用。

### edu-agent 例外：纯 skill，依赖需手动准备

`freeglm-edu-agent` 是**纯 skill**（没有 MCP server），所以「装插件不用手动 pip」对它**不适用** —— `uvx` 不会替它装任何东西，运行时依赖要自己备齐：

| 依赖 | 供哪些功能 | 安装 / 检查 |
|------|-----------|-------------|
| **Node.js + npm/npx**（≥18） | 脚手架 + 渲染（`npx hyperframes`） | `node -v` |
| **hyperframes CLI** | `init` / `lint` / `validate` / `render` | `npx hyperframes` 按需拉取（脚手架时需能访问 npm registry，之后项目内 pin 版本） |
| **Headless Chromium + 系统库** | `npx hyperframes render`（puppeteer）+ 渲染后 QA 门禁 | puppeteer 首次 `npx hyperframes` 时自动下载；最小化 Linux 上还需 `apt install libnss3 libatk-bridge2.0-0 libgbm1 libasound2 libxkbcommon0 libgtk-3-0 fonts-noto-cjk`（否则 Chrome 起不来 / 中文显示成豆腐块）。可用 `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium` 复用系统 Chrome |
| **Python 包** `dashscope` `soundfile` `numpy` `requests` | Step 3 TTS 合成与拼接 | `python3 -m pip install dashscope soundfile numpy requests` |
| **ffmpeg** | 响度归一化（`loudnorm`）+ 渲染后抽帧自查 | `apt install ffmpeg` · `brew install ffmpeg` |
| **`DASHSCOPE_API_KEY`** | Qwen-TTS（`qwen3-tts-flash`） | 从 shell 继承 |

> 网络边界：`npx hyperframes init` 和 TTS 调用需联网；**渲染本身是离线的**（所以字体 / KaTeX / GSAP 要自托管进 `dist/`）。完整清单见该 skill 的 `SKILL.md` → "Prerequisites（环境准备）"。

### 常用环境变量

配置先从 shell 环境读取；变量不存在时再回退到由安装器管理的 `~/.freeglm/config`，因此 GUI 启动的 harness 也能读取。请通过 `bash install.sh configure`（或 `<entry> --setup`）交互配置凭据，不要把密钥值粘进命令或文档。自动化场景应通过 secret store 注入下表中的常用环境变量名。本表有意不穷举：[`install.sh`](../../install.sh) 的 `CONFIG_SPEC` 是与运行时同步的可执行完整目录，可通过 `bash install.sh configure` 浏览。

| 变量 | 用于 | 默认 |
|---|---|---|
| `DASHSCOPE_API_KEY` | vision_chat · ocr · grounding（Qwen 后端）· transcribe_audio · 生成 · video-memory 构建 | *(这些功能必填)* |
| `ZHIPU_API_KEY` | vision_chat · ocr · grounding —— GLM-4.6V-Flash 后端；只设这一个时自动选中 | *(智谱后端必填)* |
| `ZHIPU_BASE_URL` | 覆盖智谱端点 | 智谱兼容 URL |
| `ZHIPU_VISION_MODEL` | 智谱后端的默认 VL 模型 | `glm-4.6v-flash` |
| `SERPER_API_KEY` | web_search · web_extractor · image_search | *(这些功能必填)* |
| `DASHSCOPE_BASE_URL` | 覆盖 DashScope 端点 | DashScope 兼容地址 |
| `SAM3_SERVER_URL` | `segmentation`（SAM3 服务） | *(分割必填)* |
| `ASR_SERVER_URLS` | `transcribe_audio` 自建兜底（逗号分隔、轮询），DashScope 失败时用 | *未设 → 仅用 DashScope* |
| `FREEGLM_FFMPEG_TIMEOUT` | ffmpeg 超时（秒） | `120` |
| `FREEGLM_CHAT_TIMEOUT` | OpenAI 兼容聊天请求超时（秒） | `600` |
| `FREEGLM_MAX_TOTAL_FRAMES` | 单个视频最多抽帧数 | `600` |
| `FREEGLM_CACHE` | 渲染派生产物的缓存目录 | 系统缓存目录 |
| `FREEGLM_CONFIG_DIR` | 覆盖 GUI harness 读取密钥的配置目录 | `~/.freeglm` |
| `FREEGLM_CONFIG` | 覆盖配置文件的完整路径 | `<配置目录>/config` |

> **blender / freecad** 是瘦客户端 —— 它们连接到一台**正在运行**、装好随包 addon 的 Blender / FreeCAD。`FREEGLM_AUTOLAUNCH=1`（插件清单里默认预设）会在第一次工具调用时把应用拉起来，Linux-x86_64 上缺应用时自动下载。完整安装、环境变量与排障见 [`cookbooks/blender`](../../cookbooks/blender/usage.md) / [`cookbooks/freecad`](../../cookbooks/freecad/usage.md)。

## 目录结构

```
src/
├── capabilities/            #   每个能力一个目录（可包含 skill 或配套的 mcp tools）
│   ├── core/                #     本地 I/O：read_image / read_video / visualize / crop / draw_bbox / …
│   ├── api/                 #     云端媒体理解：vision_chat / ocr / grounding / Omni / ASR / segmentation
│   ├── video-memory/        #     长视频记忆：层次图 + 语义检索
│   ├── video-edit/          #     视频剪辑 + 图片/视频/音频生成
│   ├── blender/             #     Blender 瘦客户端（随包 addon：vendor/ + --launch-app）
│   ├── freecad/             #     FreeCAD 瘦客户端（随包 addon：vendor/ + --launch-app）
│   └── example/             #     模板：skill + tools
├── shared/                  #   共享库（env/content/image/video/cache/syscmd/api_openai/api_dashscope 等可复用代码）
└── mcp_framework.py         #   共享框架（工具自动注册 + FastMCP serve）
pyproject.toml               # 唯一分发包 freeglm（入口 / extras / 版本）
.claude-plugin/  tests/  ruff.toml   # .claude-plugin/marketplace.json = 原生插件市场
```
