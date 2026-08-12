# vision-mcp

极简视觉 MCP server：**让纯文本模型通过云端视觉模型"看图"**。

所有工具都只返回**文字**——图片在云端视觉模型处理，模型侧永远只收到文本。
因此对不支持图像输入的模型（如 deepseek-v4-flash）100% 可用，也兼容任何支持视觉的模型。

## 工具

| 工具 | 作用 |
|---|---|
| `vision_chat(images\|videos, text, ...)` | 看图问答 / 描述（核心）；支持视频自动抽帧 |
| `ocr(images, ...)` | 图片文字识别（原样返回） |
| `grounding(images, ...)` | 目标定位：返回 `[{"label","bbox_2d":[x1,y1,x2,y2]}]`（0-1000 归一化坐标） |
| `media_info(path)` | ffprobe 探测视频/音频元数据（时长/分辨率/fps/编码/音轨） |
| `clear_memory()` | 清空当前会话的视觉问答记忆 |

## 内置机制

1. **指数退避重试** — 429/5xx/网络错误自动等待后重试（免费 GLM 限流常态，稳定性关键）；
   主选模型（4.6 Flash）只重试 1~2 次，仍失败立即切兜底模型，避免反复撞限流拖长耗时
2. **GLM 免费家族自动兜底** — `glm-4.6v-flash` 限流/超时 → `glm-4v-flash`（全程零费用）
3. **视频抽帧** — ffmpeg 动态 fps 抽帧（默认 ≤12 帧），逐帧分析后汇总；临时帧用完即清理
4. **图片 base64 内容哈希缓存** — `~/.cache/vision-mcp/`，同一文件不重复编码
5. **轻量会话记忆** — 进程内保留最近 N 轮问答（默认 4），多轮追问同一张图自动带上前文；
   `memory=false` 关闭、`clear_memory()` 清空、`VISION_MCP_MEMORY=0` 全局关

## 后端（provider）

| provider | 模型 | 端点 | Key |
|---|---|---|---|
| `zhipu` | `glm-4.6v-flash`(4.6 Flash 主选) → `glm-4v-flash`(V4 Flash) 自动兜底（全免费） | `https://open.bigmodel.cn/api/paas/v4` | `ZHIPU_API_KEY` |
| `qwen` | `qwen3.7-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `DASHSCOPE_API_KEY` |
| `auto`（默认） | 固定走 zhipu GLM 免费家族兜底链，**不切 qwen** | — | — |
| 自定义 | 传 `base_url`+`api_key`+`model` 可接任意 OpenAI 兼容端点（含 Doubao Vision） | — | — |

key 读取顺序：**环境变量 > `~/.qwen-mm-plugins/config` > 报错**。

## 运行

```bash
# 作为 MCP server（stdio），由 Agent 拉起：
python vision_server.py

# 依赖：仅 mcp + openai
pip install mcp openai
```

任意支持 MCP 的 Agent 都能接入，只需注册一个 stdio server：
`python /path/to/vision_server.py`

### ZCode 接入（已配置好）

单一插件市场 `vision-mcp`，插件名 `vision-mcp`，重启 ZCode 后即可用。
旧的双插件（qwen-mm-plugins-core / api）已移除，备份在
`~/.zcode/cli/plugins/backup-qwen-mm-plugins-*`。

## 使用示例（发给 agent 的话术）

> 看下这张截图：`vision_chat(images=["/path/to/s.png"], text="这是什么界面？列出全部文字")`
>
> 识别这张图片文字：`ocr(images=["/path/to/doc.png"])`
>
> 看这个视频：`vision_chat(videos=["/path/to/clip.mp4"], text="视频里发生了什么？")`
>
> 定位图中物体：`grounding(images=["/path/to/photo.png"], text="找到所有车辆")`
>
> 用千问看这张图：`vision_chat(images=[...], provider="qwen")`

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `VISION_MCP_MEMORY` | `1` | `0` 关闭会话记忆 |
| `VISION_MCP_MEMORY_ROUNDS` | `4` | 记忆轮数 |
| `VISION_MCP_MAX_FRAMES` | `12` | 视频抽帧上限（最大 64） |

## 注意

- GLM 兜底链：**4.6 Flash(glm-4.6v-flash) → V4 Flash(glm-4v-flash)**，全是免费模型。
  显式传 `glm-*` 模型也会挂上这条兜底链；`qwen`/自定义端点只试指定模型，不加别的。
  整个流程默认只用免费 GLM 模型，不会调用 qwen 或其他模型。
- `glm-4v-flash` 的 `max_tokens` 上限为 1024，server 会在兜底到它时自动钳制。
- 图片支持本地路径（自动 base64）或 http(s) URL。
- `dry_run=true` 可预览请求结构（不真实请求，不消耗额度）。
