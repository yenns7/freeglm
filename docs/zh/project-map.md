# FreeGLM 项目地图

本页集中说明目录职责和能力适用性。描述应维护在能力或目录边界；只有公开契约、非显然算法，
或需要专门溯源的复制/vendor 内容，才在单个文件内补充额外说明，不要逐文件重复堆注释。

## 能力目录

| 能力 | 适合 | 不应视为 | 运行与组合边界 |
|---|---|---|---|
| `freeglm-core` | 本地图片/视频读取、媒体元数据、受支持文件可视化、裁剪、框选标注、保存帧 | 云端 OCR/VQA/grounding、任意未知格式、全片语义记忆 | 本地 MCP server；部分格式需系统渲染器。外部理解组合 `api`，长视频问答组合 `video-memory` |
| `freeglm-api` | 外部 VQA、OCR、空间 grounding、Omni 音视频任务、专用 ASR、SAM3 分割 | 本地文件查看器、网页事实核验、长视频记忆 | 联网服务。GLM 只覆盖 `vision_chat`/`ocr`/`grounding`；其余模型族保留各自服务依赖 |
| `freeglm-search` | 网页事实、页面抽取、反查图核验 | 媒体读取器，或仅凭外观作结论 | 需要 Serper/网络；本地反查图会离开本机，必须取得明确同意 |
| `freeglm-video-memory` | 30 分钟及以上视频（含长视频目录）的全片问答和语义导航 | 帧级视觉证据，也不是每个短视频的默认路径 | 构建会写入 `<video>.memory/` 并调用外部服务；帧级断言前必须用 `core` 回看窄时间窗 |
| `freeglm-video-edit` | 剪辑用户提供的真实素材；能力自带图片/视频/音频生成工具 | 通用视频问答，或跳过素材检查的替代方案 | 剪辑 skill 负责时间线；感知用 `core`，只有需要外部分析时用 `api`，长素材语义导航才用 `video-memory` |
| `freeglm-blender` | Blender 场景/资产创作、精修、材质、灯光、渲染 | 参数化工程 CAD | 连接运行中的 Blender + addon；资产搜索/下载和生成工具可能访问外部服务 |
| `freeglm-freecad` | 参数化零件/装配、工程导出、零件库、FEM/CalculiX | 艺术网格建模或通用渲染 | 连接运行中的 FreeCAD + addon；FEM 还需 CalculiX |
| `freeglm-edu-agent` | 从文字或题目图片生成分步中文数学及受支持 K–12 理科讲解视频/页面 | 通用演示文稿生成器或 MCP server | 纯 skill；使用 Node/HyperFrames/Chromium/ffmpeg，并把旁白文本发送给 DashScope TTS |
| `freeglm-example` | 开发新能力的模板 | 从 marketplace 安装的生产能力 | 不在 marketplace 列出；示例 API 调用可能访问已配置的 OpenAI-compatible 端点 |

## 仓库职责

| 路径 | 职责 | 维护规则 |
|---|---|---|
| `src/capabilities/<name>/skill/` | 单项能力的 Agent 路由、流程、安全和质量门禁 | `SKILL.md` frontmatter 说明触发与排除项，不得宣称另一能力拥有的工具 |
| `src/capabilities/<name>/freeglm_<name>/` | 单项能力的 MCP server 实现 | 工具 schema 是参数与副作用的可执行事实来源 |
| `src/shared/` | 跨能力环境、媒体、content、重试、缓存、OSS 和 provider 帮助函数 | provider-neutral 逻辑放这里；能力不得导入兄弟 server 包 |
| `src/mcp_framework.py` | 工具发现、schema 归一化、server transport、启动/系统检查 | 只放共享基础设施，不写能力营销声明 |
| `.claude-plugin/`、`.zcode-plugin/`、各能力 plugin 目录 | Marketplace 与 harness 注册 | 描述应从能力归属生成或受校验；manifest 不重新定义工具归属 |
| `cookbooks/` | 实战示例和已观察工作流 | 示例必须披露网络、凭据和数据出境前提 |
| `docs/en/`、`docs/zh/` | 安装、开发、路由和架构说明 | 中英文策略必须保持语义一致 |
| `tests/` | 离线契约与凭据门控的连通性测试 | live test 被跳过不能表述为外部服务已通过 |
| `NOTICE`、`UPSTREAM.md`、能力级 `NOTICE.md` | 上游和 vendor 代码溯源 | 记录精确来源 revision，并保留必要声明 |

## 根级与控制文件

下表集中回答仓库入口和策略控制文件“负责什么、何时适用”。这样不必把相同描述复制到每个文件中。

| 文件或分组 | 职责与适用场景 | 维护边界 |
|---|---|---|
| `README.md` | 英文首屏、受支持能力概览、安装入口和安全首轮路由 | 保持精简；详细归属和排除项链接到本目录 |
| `README.zh.md` | `README.md` 的中文对应文档 | 策略和能力声明与英文保持语义一致 |
| `install.sh` | 源码 checkout 的交互式安装、profile 选择、harness 注册、系统检查和隐藏凭据配置 | 操作入口；不得打印 secret，也不得暗示所有可选依赖都会安装 |
| `.env.example` | 已识别配置项名称与非敏感默认值清单 | 只用于说明；不得保存凭据值，也不得指示用户把值暴露到聊天或命令输出 |
| `pyproject.toml` | Python 分发元数据、依赖 profile、命令入口、包布局和测试配置 | Packaging 事实来源；能力适用性仍以本目录及各能力 tool/skill 契约为准 |
| `CLAUDE.md` / `AGENTS.md` | Agent harness 操作指令和仓库贡献约束 | 只在加载它们的 harness/目录作用域内适用，不会增加运行时能力 |
| `SECURITY.md` | 漏洞报告、凭据处理策略和数据出境安全边界 | 属于安全策略而非安装教程；报告必须移除 secret 和私有媒体 |
| `CONTRIBUTING.md` | 贡献者环境、变更流程、验证要求和 pull request 指南 | 适用于仓库改动，不负责终端用户的能力路由 |
| `LICENSE` / `NOTICE` / `UPSTREAM.md` | 项目许可证、必要第三方声明、精确上游导入基线及关系 | 保留必要原文；再次导入上游时，用不可变 revision 更新 `UPSTREAM.md` |
| `scripts/check_manifests.py` | 检查能力注册和生成 manifest 的一致性 | 能力、plugin、entry point 或 marketplace 元数据变化后运行 |
| `scripts/check_security_contract.py` | 检查全仓凭据处理和安全文档契约 | installer、配置、凭据、日志、tool schema 或安全策略变化后运行 |
| `scripts/gen_env_docs.py` | 从维护中的配置定义生成或校验环境变量文档 | 配置名称新增、重命名或删除后运行；不要把清单手工复制进多份文档 |
| Vendor 代码（`**/vendor/`） | 为运行时集成保留的第三方源码 | 以最近的 notice/license 为准并保留溯源，不为统一本地风格而改写。Blender vendor 树中服务商公开发布的共享试用标识属于公开、受限额的 vendor 数据，不是用户 secret；绝不能用私人凭据替换 |
| 资产（`**/assets/`） | 各能力随包提供的视觉、字体、fixture 或模板资源 | 在目录/catalog 层说明溯源和复用规则，不为每个 asset 单独堆描述 |
| 生成文件与构建产物 | 由仓库生成器、打包、测试或用户工作流产生的内容 | 从所属事实来源重新生成；除非格式明确要求，不逐文件编辑或补注释 |

## 网络、数据出境与凭据

| 能力/路径 | 可能离开本机的内容 | 目的地/边界 |
|---|---|---|
| `core` | 给 URL-aware renderer 的 URL 会被抓取；其余本地文件操作保持本地 | 目标 URL，以及工作流显式调用的外部渲染器 |
| `api` | Prompt、图片、采样帧、音频或视频；超大媒体可能上传到用户配置的 OSS | 配置的 DashScope、智谱、SAM3/ASR 服务或 OSS 端点 |
| `search` | 搜索词和待读取 URL；本地反查图在明确同意后上传 | Serper、目标网站和文档所述第三方公开图床 |
| `video-memory` | 构建记忆时的视频片段/帧、音频/ASR 内容和生成的语义摘要 | DashScope 和可选的用户自配 OSS |
| `video-edit` / `edu-agent` | 生成 prompt、所选生成服务接受的源媒体，或旁白文本 | 所选 DashScope 生成/TTS 服务 |
| `blender` / `freecad` | live-app 命令通常留在本机；可选搜索、下载、生成或自动安装会访问其文档来源 | 本地 addon，以及显式选择的外部资产/provider 端点 |

凭据属于配置，不属于任务内容：

- 只能通过进程环境变量或私有的 `~/.freeglm/config` 提供。
- 不得粘贴到聊天、prompt、issue、日志、源码、命令输出或工具参数。
- Agent 可以检查凭据是否存在，但不得读取、打印、echo、总结或转发其值。
- 任何会公开本地/私有媒体，或把它发送给用户请求未隐含的 provider 的操作，都要先取得明确同意。

## 事实来源顺序

描述冲突时按以下顺序判断：

1. 可执行工具 schema 与实现：实际参数和副作用。
2. 能力 `SKILL.md`：触发、流程和组合策略。
3. 本目录：归属与高层适用性。
4. Marketplace 文案与 cookbooks：发现与示例。

核对可执行行为后修正上层文案，不要把同一修正段落复制进每个文件。
