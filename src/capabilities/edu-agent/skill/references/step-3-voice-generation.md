# Step 3: Voice Generation

Generate standard Mandarin TTS audio with sentence-level timestamps. Audio and timestamps are produced in a single step — **no Whisper transcription needed**.

## TTS Strategy — DashScope Qwen-TTS (`qwen3-tts-flash`), synthesized per-sentence in parallel

**用 DashScope SDK 调用 Qwen-TTS（`dashscope.MultiModalConversation`，模型 `qwen3-tts-flash`），面向用户交付，音质优先。**

这是该技能支持的云端产品路径：直接用官方 DashScope SDK 调 Qwen-TTS，无需自己部署 TTS 节点、无需拼推理 URL、
无需管理推理服务器。合成质量、可用性和延迟取决于所选模型、账号配额及服务状态，交付前仍需试听检查。

> **为什么用 `qwen3-tts-flash`（HTTP）而不是 `tts_v2.SpeechSynthesizer`（WebSocket）？**
> `qwen3-tts-flash` 走 HTTP `MultiModalConversation.call`，返回一个音频 URL（WAV，~24h 有效），
> 稳定、无需 WebSocket 通道。`dashscope.audio.tts_v2.SpeechSynthesizer` 走 wss，部分环境的
> 出网策略会拦截 WebSocket 导致 `ConnectionError`。因此这里统一用 HTTP 的 `qwen3-tts-flash`。

**如何兼顾吞吐量与分句时间轴？** 逐句串行请求会慢，因此这里**按句并发合成**：用有界线程池发起
合成请求，再按原顺序把返回的音频拼接起来。实际耗时取决于服务延迟、限流和重试。时间戳由**每句返回
音频的实测时长**计算，而不是按字数估算。

- **Official SDK, no self-hosting.** 用 `MultiModalConversation.call(model="qwen3-tts-flash", ...)`，不请求任何自建 `http://.../tts`。
- **Parallel per-sentence.** 使用有界线程池并发（默认 8 worker），并在限流时降低并发度。
- **Measured timestamps.** 每句边界来自返回音频的实测时长。

Each sentence duration is measured from its returned audio clip, producing both `narration.wav` and `transcript.json` in one pass with measured sentence boundaries.

## 1. Environment Setup

Install dependencies if not already present:

```bash
pip install dashscope requests soundfile numpy
```

Audio decoding/assembly uses **`soundfile`** (Qwen-TTS returns WAV, which soundfile reads natively — no `pydub`/`audioop`, so this works on Python 3.13). ffmpeg is still needed for the loudness-normalization step below.

**DashScope credential.** The synthesis script (`scripts/generate_voice.py`) resolves the credential from the process environment first and then the private `~/.freeglm/config` file. Configure it **outside the agent conversation** using one of these paths:

1. From a source checkout, run `bash install.sh configure`. The installer accepts the value through hidden input and writes the private config with mode `0600`.
2. In a managed runtime or CI system, let its secret manager inject the value into the process environment.
3. If the installer is unavailable, use a trusted local credential editor that accepts hidden input and writes `~/.freeglm/config` with mode `0600`; do not display the file contents.

The agent must never request, read, print, log, or repeat the secret, and must never place it in chat, tool arguments, command history, generated scripts, or source files. A presence check may report only whether configuration exists.

**No `sherpa-onnx`, `openai-whisper`, `torch`, `pydub`, or `opencc` dependency.**

## 2. Model & Voice

| Item | Value | Notes |
|------|-------|-------|
| `model` | `qwen3-tts-flash` | HTTP `MultiModalConversation`; returns a WAV URL (~24h validity). |
| `voice` | `Cherry` | System voices: `Cherry` (young female), `Serena` (female, professional), `Ethan` (male), `Chelsie` (female, warm), +40 others. |
| `language_type` | `Chinese` | Specifying the language significantly improves synthesis quality. |

## 3. Prepare Narration Text

Extract plain narration text from `SCRIPT.md` into `narration-script.txt` — strip all markdown headers (`##`), horizontal rules (`---`), and timing annotations (parenthetical notes like `(3-5s)`). Keep only the spoken Chinese text.

## 4. Generate TTS Audio + Timestamps

Run the shipped synthesis script from the project root (the parent of `dist/`):

```bash
EDU_SKILL_ROOT="<absolute directory containing freeglm-edu-agent/SKILL.md>"
python3 "$EDU_SKILL_ROOT/scripts/generate_voice.py" narration-script.txt
```

It synthesizes every sentence concurrently via the DashScope SDK, downloads each clip, then assembles `narration.wav`, `transcript.json`, and `captions.json` in one pass with exact per-sentence timestamps (measured from each returned clip's real duration). **The script reads `DASHSCOPE_API_KEY` itself** (environment → `~/.freeglm/config` → default) — so it works in GUI-launched harnesses, and you never handle the plaintext key. Do not re-author this as an inline snippet; the logic (sentence split, parallel synthesis, duration-measured timestamps) is fixed and tested.

**Flags** (all optional):

| Flag | Default | Notes |
|------|---------|-------|
| `--model` | `qwen3-tts-flash` | HTTP path; returns a WAV URL |
| `--voice` | `Cherry` | Keep one consistent voice per video (`Serena` / `Ethan` / `Chelsie` / ...) |
| `--language` | `Chinese` | Improves synthesis quality |
| `--workers` | `8` | Parallel sentence synthesis; raise to go faster, but stay under the account QPS limit |
| `--pause` | `0.3` | Silence (s) inserted between sentences |
| `--wav` / `--transcript` / `--captions` | `narration.wav` / `transcript.json` / `captions.json` | Output paths |

> **Rate limits:** if failures come in bursts, lower `--workers`. A per-sentence retry (3 attempts) handles transient errors.
>
> **Missing credential:** run `bash install.sh configure` outside the agent conversation, or have a trusted secret manager inject it into the process environment. Do not paste the value into chat or a tool call.

## 4b. Normalize Audio Volume

Apply EBU R128 loudness normalization using ffmpeg to ensure consistent volume throughout the narration.

```bash
ffmpeg -i narration.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 44100 narration_normalized.wav -y
mv narration.wav narration_original.wav
mv narration_normalized.wav narration.wav
```

## 5. Map Timestamps to Scenes

After generation, map the sentence timestamps to scene boundaries from `SCRIPT.md`. Update `STORYBOARD.md` with actual timing:

```markdown
| Scene | Start | End | Duration |
|-------|-------|-----|----------|
| 开场引入 | 0.0s | 4.2s | 4.2s |
| 题目朗读 | 4.2s | 12.8s | 8.6s |
| 思路分析 | 12.8s | 22.1s | 9.3s |
| 解题步骤一 | 22.1s | 33.5s | 11.4s |
| ...   | ...   | ... | ... |
```

Locate scene boundaries by matching the first sentence of each section in `transcript.json`.

## Quality Check

1. Verify `narration.wav` exists and is non-empty.
2. Verify `transcript.json` has reasonable sentence boundaries (one segment per sentence).
3. If a math term is mispronounced, adjust `narration-script.txt`:
   - Spell out terms more explicitly (e.g., "x的平方" instead of "x平方")
   - Replace unsupported symbols with spoken equivalents
   - Re-run `python3 "$EDU_SKILL_ROOT/scripts/generate_voice.py" narration-script.txt` after adjustments

## Gate

Before proceeding to Step 4:
- [ ] `narration.wav` exists and is non-empty Mandarin audio
- [ ] `transcript.json` exists with sentence-level timestamps (one segment per sentence)
- [ ] `captions.json` exists (same content as transcript.json — original script text with precise timestamps)
- [ ] Caption text matches `narration-script.txt` exactly
- [ ] Scene boundaries mapped with actual timestamps
