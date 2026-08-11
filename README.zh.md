# FreeGLM

[English](README.md) · **中文**

基于 Qwen-MM-Plugins 二次开发 · 新增智谱免费 GLM 视觉后端。

FreeGLM 是在 Qwen 团队开源的 [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins)（Apache-2.0）基础上继续改造的衍生项目。它保留并扩展上游可按能力安装的多模态 Agent Skills 与 MCP servers，并新增智谱当前免费的 GLM-4.6V-Flash 模型，作为 `vision_chat`、`ocr`、`grounding` 的可选视觉后端。免费状态以智谱当前官方政策为准；后端选择遵循明确配置，不会根据价格或延迟自动择优。

## 目录

- [🧩 能力](#-能力)
- [🏗 架构](#-架构)
- [🗺 项目地图](docs/zh/project-map.md)
- [🤖 Agent 接入与路由](docs/zh/agent-integration.md)
- [📦 安装](#-安装)
- [🔧 依赖](#-依赖)
- [🔑 配置](#-配置)
- [🔌 Provider 与 API 配置](docs/zh/provider-setup.md)
- [🚀 快速开始](#-快速开始)
- [🤖 给 Agent 的快速接入提示词](#-给-agent-的快速接入提示词)
- [🧪 开发](#-开发)
- [📄 License 与署名](#-license-与署名)

## 🧩 能力

每个能力单独安装 —— 一个 **skill**（让模型知道有这套工具）+ 一个可选的 **MCP server**（工具本体）。

我们提供了一组 [**cookbooks**](cookbooks/),展示这些插件的实战效果 —— 每个能力的 cookbook(见下表各行)含完整工具清单、安装与实测案例。

| 能力 | 做什么 | 安装名 | Cookbook |
|---|---|---|---|
| **core** | 本地 I/O：读取图片/视频、检查媒体元数据、可视化受支持的文档/数据/代码/3D/GIS/notebook 格式，以及裁剪、标注或保存帧 | `freeglm-core` | [link](cookbooks/core/usage.md) |
| **api** | 外部媒体理解服务。`vision_chat` / `ocr` / `grounding` 支持 DashScope Qwen 或智谱当前免费的 GLM-4.6V-Flash；Omni、专用 ASR 与 SAM3 分割各有自己的服务依赖 | `freeglm-api` | [link](cookbooks/api/usage.md) |
| **search** | 通过 Serper 做网页搜索、页面抽取和反查图。本地图片反查会上传到第三方公开图床，必须先取得用户明确同意 | `freeglm-search` | [link](cookbooks/search/usage.md) |
| **video-memory** | 长视频记忆：层次化图记忆，支撑超长视频问答 | `freeglm-video-memory` | [link](cookbooks/video-memory/usage.md) |
| **video-edit** | 视频剪辑 + 生成：剪辑工作流 + 图片 / 视频 / 音频生成 | `freeglm-video-edit` | — |
| **blender** | Blender 三维建模：对一个**正在运行**的 Blender 写 Python（瘦客户端，22 工具）—— 建模 / 材质 / 灯光 / 渲染 | `freeglm-blender` | [link](cookbooks/blender/usage.md) |
| **freecad** | FreeCAD 参数化 CAD：驱动一个**正在运行**的 FreeCAD（瘦客户端，14 工具）—— 建模、改属性、STEP/STL 导入导出、FEM 分析 | `freeglm-freecad` | [link](cookbooks/freecad/usage.md) |
| **edu-agent** | 讲题视频：把一道数学 / 理科题或题目图片变成一步步讲解的中文视频 / 交互页面（**纯 skill**，无 MCP server） | `freeglm-edu-agent` | — |

## 🏗 架构

![FreeGLM 架构](docs/assets/architecture.svg)

目录职责、能力边界、依赖和数据出境行为见[项目地图](docs/zh/project-map.md)；工具选择、长视频路由和多 Agent 协作见 [Agent 接入与路由](docs/zh/agent-integration.md)。

## 📦 安装

一个能力 = 一个 **skill**（让模型知道有这套工具）+ 一个可选的 **MCP server**（工具本体，`uvx` 按需拉起 —— 依赖 [uv](https://docs.astral.sh/uv/)，不用手动 pip）。

### 推荐：引导式安装器

一个脚本搞定 **install · configure · verify · uninstall**，覆盖它支持的所有 harness（Claude Code · Codex · Qoder · OpenClaw · Qwen Code · Gemini CLI）。它底层调各 harness 自己的原生安装 —— 不重造轮子 —— 并把配置写进统一的 `~/.freeglm/config`（GUI / 终端都读），一次配好：

```bash
curl -fsSL https://raw.githubusercontent.com/yenns7/freeglm/v1.0.2/install.sh | bash   # 引导菜单
```

**ZCode** 不在 `PATH` 上提供插件 CLI。打开一个 workspace，然后按 **Settings → Plugins → Create → Add marketplace URL → Install** 为每项所需能力安装。仓库在 `.zcode-plugin/` 下自带 ZCode 就绪清单；精确界面流程和清单模型见 [ZCode 适配指南](docs/zh/adapting_zcode.md)。

也可以只跑单个动作 —— `bash install.sh install` / `configure` / `verify` / `uninstall`（`configure` 和 `verify` 各自做什么，见下面的[配置](#-配置)与[依赖](#-依赖)）。

**Windows x64：**推荐使用 WSL2（建议 Ubuntu），在 WSL home 目录中 clone 仓库
（例如 `~/code`），不要放在 `/mnt/c` 这类 Windows 挂载盘下，然后运行相同命令。
当前 Windows 仅支持 WSL2；原生 Windows 尚未完成验证。简要说明见
[Windows 安装说明](docs/zh/installation.md#windows-wsl2)。

### 手动（逐 harness）

想用 harness 自己的命令，或你在 opencode / pi / QwenPaw 上（安装器不覆盖这几个）？那就自己注册 skill + MCP。

**有插件市场的 harness**（Claude Code · Qoder · Codex · OpenClaw · Qwen Code）—— 加市场，再装某个能力（把 `<cap>` 换成 `core` / `api` / `search` / `video-memory` / `video-edit` / `blender` / `freecad`）。Agent 需要检查本地文件/媒体时安装 `core`，再只添加工作流实际需要的独立云端、搜索、剪辑或应用能力：

```bash
# Claude Code
claude   plugin  marketplace add https://github.com/yenns7/freeglm.git
claude   plugin  install       freeglm-<cap>@freeglm
# Qoder
qodercli plugins marketplace add https://github.com/yenns7/freeglm.git
qodercli plugins install       freeglm-<cap>@freeglm
# Codex
codex    plugin  marketplace add https://github.com/yenns7/freeglm.git
codex    plugin  add           freeglm-<cap>@freeglm
# OpenClaw
openclaw plugins install       freeglm-<cap> --marketplace https://github.com/yenns7/freeglm.git
# Qwen Code
qwen extensions install https://github.com/yenns7/freeglm.git:freeglm-<cap> --consent
```

`marketplace add` 也接受本地仓库路径；重复执行是安全的。在 **codex** 上，`marketplace add` **不会**刷新已添加的 marketplace，所以要装入新增能力时，先执行 `codex plugin marketplace upgrade freeglm` 再 `plugin add`。

**其它 harness**（Gemini CLI · opencode · pi · QwenPaw · **ZCode** · …）在各自配置里注册 skill + MCP —— 各 harness 的精确配置块见 [`docs/zh/installation.md`](docs/zh/installation.md) 与 [ZCode 适配指南](docs/zh/adapting_zcode.md)。最省事：**直接让 agent 帮你装** —— 「装一下 `freeglm-<cap>`」。

## 🔧 依赖

`uvx` 首次启动时按 profile 把 Python 依赖装进隔离缓存 —— 不用手动 pip。需要你自己装的只有**系统工具**：`ffmpeg`（视频 / 音频），外加 `visualize` 可选的 `libreoffice` / `blender` / `texlive` / `chromium`。跑 `bash install.sh verify` 自检已装的能力 —— 它会确认 API key、并报告缺哪些系统工具（内部对每个能力预拉起 uvx 环境并跑 `--check-system`）。完整系统工具表、edu-agent（纯 skill）的准备、以及 blender/freecad 瘦客户端说明，见 [`docs/zh/installation.md`](docs/zh/installation.md)。

## 🔑 配置

API 类工具需要 key —— 原生读图 / 视频 / 文档不需要：

- `ZHIPU_API_KEY` —— 把智谱当前免费的 **GLM-4.6V-Flash** 模型作为 `vision_chat` / `ocr` / `grounding` 的视觉后端。只设这一个 key，VL 工具就会自动路由到智谱（无需 DashScope）；免费状态以智谱官方政策为准。可选：`ZHIPU_BASE_URL`、`ZHIPU_VISION_MODEL`
- `DASHSCOPE_API_KEY` —— `vision_chat` / `ocr` / `grounding`（Qwen 后端）/ `transcribe_audio` / Omni 音视频理解 / 生成类 / video-memory 构建
- `SERPER_API_KEY` —— `web_search` / `web_extractor` / `image_search`

在 shell 里 export，或写进 `~/.freeglm/config`（仅当变量未在环境中时才读取 —— 这样 GUI 启动的 harness 也能拿到）。引导式安装器的 Configure 步骤会帮你写这个文件：

```bash
bash install.sh configure     # 交互式：API key、端点、目录、OSS、主机地址 —— 整份分组配置
```

凭据只能保存在进程环境变量或私有的 `~/.freeglm/config` 中。绝不要把 key 粘贴进聊天、echo 到日志、提交到仓库，或作为工具参数传入。Agent 可以检查凭据是否已配置，但不得读取或显示其值。外部能力会把查询或媒体发送给所配置的服务商；处理私有材料前先查看[数据出境表](docs/zh/project-map.md#网络数据出境与凭据)。

GLM / DashScope / Serper 的安全配置、分层验收与排障见
[Provider 与 API 配置指南](docs/zh/provider-setup.md)；非交互 / 自动化配置与环境变量表见
[`docs/zh/installation.md`](docs/zh/installation.md)。

## 🚀 快速开始

装好某个能力后，在 harness 里引用文件直接提问，模型会自动调用对应工具。读取是**动态分辨率**的：每张图片、每帧视频、每页文档都会自动缩放到 VL 模型的 patch grid —— 一张 4K 截图上的细小文字和一张小缩略图都能以各自需要的清晰度读进来，无需手动缩放。

```text
# core —— 读图片 / 视频 / 文档 / 3D 模型（本地、动态分辨率）
@dashboard-4k.png      读出这张仪表盘里的每一个数字。
@report.pdf            总结第 3 页。

# api —— 云端 VL + Omni API。VL 工具在只设 ZHIPU_API_KEY 时自动走 GLM-4.6V-Flash，
#        否则走 DashScope Qwen；Omni / ASR / 分割始终用 DashScope。
@receipt.jpg           OCR 这张小票并把各行金额加总。                        # VL（GLM 或 Qwen）
@street.jpg            把画面里每一辆车都框出来。                            # grounding
@meeting.mp4           带说话人标签和时间戳转写这段会议。                    # omni
@sports-clip.mp4       统计每次成功传球，并列出发生时间。                    # omni
@song.mp3              标注曲风、情绪、乐器、调性和人声特征。                # omni

# search —— 联网 + 反查图，核实画面里的东西
@place.jpg             这张照片是在哪拍的？                     # image_search + web_search

# video-memory —— 对长视频提问；首次提问自动构建 memory
@lecture-2h.mp4        这段视频的主要观点是什么？带上时间戳。

# video-edit —— 图片 / 视频 / 音频生成 + 剪辑工作流
                       生成一张 1024×1024 的图：小熊猫在深夜敲代码。
@/path/to/media        帮我把这个视频剪到大约 3 分钟。

# blender —— 驱动正在运行的 Blender 建模 / 材质 / 灯光 / 渲染（瘦客户端，22 工具）
                       建一个低多边形木凳，加一盏暖色主光，然后渲染出来。

# freecad —— 在正在运行的 FreeCAD 里做参数化 CAD（瘦客户端，14 工具；STEP/STL、FEM）
                       建一颗 M6 六角螺栓、长 30 mm，导出成 STEP。

# edu-agent —— 把一道数学 / 理科题变成一步步讲解的中文视频（纯 skill）
@geometry-problem.png  把这道题的解法讲清楚，做成带旁白的视频。
```

每个能力的全部工具、安装与实测案例见其 🍳 [cookbook](cookbooks/)。

## 🤖 给 Agent 的快速接入提示词

安装所需能力后，可把下面的精简策略粘给 Agent。完整路由和多 Agent 协作规则见 [Agent 接入与路由](docs/zh/agent-integration.md)。

```text
你有 FreeGLM 能力可用。把每项任务交给所属能力：

1. 本地读取、元数据、可视化、裁剪、标注和抽帧用 freeglm-core；只有需要外部模型/
   服务做 VQA、OCR、grounding、Omni、ASR 或分割时才用 freeglm-api。仅配置
   ZHIPU_API_KEY 且未配置 DASHSCOPE_API_KEY 时，VL 才自动选择 GLM；否则默认 DashScope
   Qwen，除非显式指定 provider。
2. 30 分钟及以上视频的全片问答用 freeglm-video-memory；短视频问答用 core；剪辑用
   freeglm-video-edit，只有长素材确实需要全片语义导航时才组合 video-memory。断言帧级细节前，
   必须回到原视频窄时间窗复核。
3. 只有核验外部事实时才用 freeglm-search。本地图片反查前必须取得明确同意；未经同意不得
   上传私有媒体。
4. 绝不索要、打印、echo、粘贴到聊天或通过工具参数传递凭据。凭据只能来自进程环境变量或
   私有的 ~/.freeglm/config。
5. 主 Agent 负责最终答案和共享文件。只把独立、有边界的工作委派给并行 Agent，为每个 Agent
   分配互不重叠的输出，再由主 Agent 统一验证和集成。
```

## 🧪 开发

开发环境、贡献规范和检查命令见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。详细指南：
[本地调试](docs/zh/local_development.md) · [添加能力](docs/zh/how_to_add_new_capability.md) ·
[测试](docs/zh/testing.md) · [Provider 配置](docs/zh/provider-setup.md) ·
[项目地图](docs/zh/project-map.md) · [Agent 接入](docs/zh/agent-integration.md)。

## 📄 License 与署名

Apache-2.0 —— 见 [`LICENSE`](LICENSE) 与 [NOTICE](NOTICE)。

本项目是 [Qwen-MM-Plugins](https://github.com/QwenLM/Qwen-MM-Plugins)（Qwen 团队，Apache-2.0）的**衍生作品**，导入基线为上游提交 [`8d6ea5a1f658260743307c52c2024ec87599fa48`](https://github.com/QwenLM/Qwen-MM-Plugins/commit/8d6ea5a1f658260743307c52c2024ec87599fa48)。FreeGLM 以独立 Git 历史发布，**不是** GitHub formal fork，因此不能把 GitHub fork 关系当作溯源依据。来源基线和本地改造范围见 [`UPSTREAM.md`](UPSTREAM.md)。

Blender 和 FreeCAD 能力内置(vendor)了第三方 MIT 许可的代码,署名见 [`src/capabilities/blender/NOTICE.md`](src/capabilities/blender/NOTICE.md) 和 [`src/capabilities/freecad/NOTICE.md`](src/capabilities/freecad/NOTICE.md)。
