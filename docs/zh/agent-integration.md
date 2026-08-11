# Agent 接入与路由

安装所需 FreeGLM 能力后遵循本策略。文件存在不代表 skill 或 MCP server 已在当前运行时启用；
规划调用前要检查实时 skill/tool 清单。能力缺失时如实报告，不得假装已经调用。

## 按任务归属路由

| 用户意图 | 主能力 | 需要时组合 |
|---|---|---|
| 读取图片/短视频、检查元数据、可视化受支持的本地文件 | `freeglm-core` | 只有需要外部模型理解时加 `api`；只有需要外部事实时加 `search` |
| OCR、caption/VQA、物体 grounding、Omni 音视频、ASR、分割 | `freeglm-api` | 用 `core` 检查本地证据，并标注返回的框 |
| 核验身份或外部事实 | `freeglm-search` | 用 `core/save_view` 选择证据；本地反查图需明确上传同意 |
| 对一个或多个 30 分钟以上视频做全片问答 | `freeglm-video-memory` | 定位区间后，用 `core/read_video` 回看窄时间窗 |
| 剪辑用户提供的真实素材 | `freeglm-video-edit` | `core` 做素材审看；`api` 做用户需要的模型分析；只有长素材导航才加 `video-memory` |
| 为剪辑生成图片、视频或语音资产 | 随 `freeglm-video-edit` 安装的生成工具 | 进入时间线前验证生成资产 |
| 创建/精修 Blender 场景 | `freeglm-blender` | 确认 Blender/addon live 连接，并检查渲染证据 |
| 创建参数化 CAD 或运行 FEM | `freeglm-freecad` | 确认 FreeCAD/addon live 连接；FEM 还需 CalculiX |
| 生成中文数学或受支持 K–12 理科讲解视频/页面 | `freeglm-edu-agent` | 纯 skill 工作流；按其声明准备 HyperFrames、浏览器、ffmpeg 与 TTS |

## 视频判断边界

1. 只要是视频剪辑，主流程都归 `freeglm-video-edit`，与时长无关。
2. 30 分钟以下视频的内容问答用 `freeglm-core`；应放大关键时间窗，不能把少量缩略帧当作完整证据。
3. 30 分钟及以上的全片问答先构建/查询 `freeglm-video-memory`。
4. Memory 是粗粒度语义索引。断言视觉细节前，必须用 `freeglm-core` 回看原视频窄时间窗。
5. 只有答案需要外部知识时才用 `freeglm-search`，不能因为一帧难看清就自动联网。

## Provider 路由

- `vision_chat`、`ocr`、`grounding` 支持 DashScope Qwen 与智谱 GLM。
- 只有配置 `ZHIPU_API_KEY` 且未配置 `DASHSCOPE_API_KEY` 时，VL 自动路由才选择智谱；
  否则默认 DashScope，除非显式选择 provider。
- 这是配置规则，不是价格、速度或质量比较。
- Omni 音视频、专用 ASR、分割、生成、搜索和 memory 构建保留各自 provider 要求；GLM 凭据
  不能启用这些服务。
- 只有实时工具 schema 明确提供 request preview/dry-run，且预览有具体诊断价值时才使用；
  它不是每个工作流的固定步骤。

## 多 Agent 协作

主 Agent 始终对任务、最终答案和共享状态负责。

只有工作可以拆成独立、有边界的输出时才委派，例如分别做来源审查、互不重叠的能力审计，
或不同资产制作。派发前，为每个 Agent 明确：

- 精确目标和完成判据；
- 互不重叠的文件或产物集合；
- 允许使用的外部服务和数据边界；
- 必须返回的证据；
- 不得在范围外发布、删除或覆盖共享状态。

紧耦合的单文件修改、需要统一判断的决策、或多个 Agent 会写同一文件的工作不应委派。
并行 Agent 不得各自产生竞争性的最终答案；主 Agent 负责审查返回证据、解决矛盾、运行集成检查，
并对外给出唯一结果。

对长视频目录，可在运行时和服务限额允许时并行构建彼此独立的单视频 memory。输出目录必须隔离，
记录每份 memory 的来源；只有所有构建均可归属且完成后才合并。

## 凭据与私有数据

- 凭据只能来自进程环境变量或私有的 `~/.freeglm/config`。
- 不得要求用户把凭据粘贴到聊天；不得通过 MCP/tool 参数、prompt、源码、shell 输出、日志、
  截图或 Agent 间消息传递凭据。
- 不得查看或显示凭据值；Agent 最多只需检查“存在/不存在”。
- 委派任务中不得携带凭据；每个 worker 只使用其所需、已安全配置的运行环境。
- 把私有媒体发送给外部 provider 前，应说明目的地；如果该传输并非用户请求中已经明确，必须先征得同意。
- 本地图片反查会在文档所述第三方图床产生公开可访问副本，必须在操作前取得明确同意。

## 失败与降级

所属能力不可用时，要说明缺少什么，以及降级会改变哪些准确性或隐私属性。不得静默替换已配置
provider、外部服务、长视频 memory 流程或视觉检查步骤。降级会实质改变数据出境、质量、费用风险
或用户要求的输出时，必须先询问。
