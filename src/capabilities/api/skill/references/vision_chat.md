# Vision Chat

## vision_chat

Calls a vision-language model via DashScope or Zhipu.

### Configuration

Credentials and endpoint overrides are process or user configuration, never tool arguments. Run
`freeglm-api --setup` for an interactive, no-echo credential prompt, or provide the variables through
your harness's protected environment configuration.

| Provider | Credential variable | Optional endpoint variable |
|---|---|---|
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_BASE_URL` |
| Zhipu | `ZHIPU_API_KEY` | `ZHIPU_BASE_URL` |

Do not paste credentials into tool calls, prompts, command arguments, or logs. A custom endpoint is
used only with credentials supplied by trusted process configuration; the public tool schema cannot
override either value.

### Tips

- Use `dry_run=true` to inspect the request payload without making a call
- Local video files are auto-extracted into frames (controlled by `video_max_frames`, default 128)
- `vl_high_resolution_images=true` raises the image token limit to 16384 (up to 16M pixels)

### Model selection

| Model | Use case |
|---|---|
| `qwen3.7-plus` | Default (vision_chat / ocr / grounding) |
