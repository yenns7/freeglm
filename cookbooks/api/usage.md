# Cookbook — FreeGLM API

`freeglm-api` calls cloud models to *understand* media. Its tools are split by model family
into three subpackages (the directory is the category):

- **`vl/`** — Qwen-VL: `vision_chat`, `ocr`, `grounding` (image/video in, text or pixel boxes out).
- **`omni/`** — Qwen-Omni audio/video: transcription, diarization, temporal grounding, event counting,
  captioning, and music analysis. These tools reason over sampled frames and the embedded audio
  together; the ASR tools send only the extracted audio track.
- **`others/`** — `transcribe_audio` (Qwen3-ASR) and `segmentation` (self-hosted SAM3).

For whole-video QA over videos around 30 minutes or longer, use
[`video-memory`](../video-memory/usage.md) instead of the per-clip tools here. For local file reading
and visualization (no cloud call), see [`core`](../core/usage.md).

---

## Tools

**VL — `shared.api_openai`, DashScope**
- `vision_chat` — call a VLM (default: `qwen3.7-plus`) for vision chat over image / video input
- `ocr` — text recognition in images
- `grounding` — object detection/localization, returning pixel bboxes (pairs with core's `draw_bbox`)

**Omni — `shared.api_omni`, DashScope**

| Tool | Use it for | Main output |
|------|------------|-------------|
| `omni_asr` | Plain speech transcription without timing | One continuous text transcript |
| `omni_asr_timestamped` | Sentence- or word-level controllable ASR | Timestamped JSON segments and SRT |
| `omni_multi_speaker_asr` | Speaker diarization — who said what and when | Speaker-labelled segments and SRT |
| `omni_av_caption` | Describe what happens throughout a clip | Time spans with a description per span |
| `omni_av_grounding` | Find **when** a natural-language event appears | Matching start/end times |
| `omni_av_counting` | Count an event, object, or action | Total count and occurrence timestamps |
| `omni_music_caption` | Analyze a complete music track | Structured music tags and a dense English caption |

**Others**
- `transcribe_audio` — speech recognition (default: `qwen3-asr`), output as SRT / text / JSON
- `segmentation` — text-prompted segmentation (self-hosted SAM3)

Every tool accepts a local `file_path` or an HTTP(S)/OSS URL and supports `dry_run=true` to preview the
model request without calling the API. The Omni video tools also accept `fps` and `max_pixels`: raise
them only when finer temporal or visual detail is worth the extra latency and token cost.

`grounding` is spatial — it answers **where** something is inside a still image. `omni_av_grounding` is
temporal — it answers **when** something happens in a clip.

---

## Install

```bash
claude plugin marketplace add https://github.com/yenns7/freeglm.git
claude plugin install freeglm-core@freeglm
claude plugin install freeglm-api@freeglm
```

---

## Requirements and configuration

| Requirement | Description |
|-------------|-------------|
| `DASHSCOPE_API_KEY` | Required — authenticates Qwen-VL (default backend), Qwen-Omni, and Qwen3-ASR requests. |
| `ZHIPU_API_KEY` | Optional — authenticates the Zhipu GLM-4.6V-Flash backend for vision_chat / ocr / grounding. When set alone (no DASHSCOPE_API_KEY), the VL tools auto-route to it; or force per call with `provider="zhipu"`. |
| `ZHIPU_BASE_URL` | Optional — overrides the Zhipu OpenAI-compatible endpoint. |
| `ZHIPU_VISION_MODEL` | Optional — default VL model for the Zhipu backend (`glm-4.6v-flash`). |
| `DASHSCOPE_BASE_URL` | Optional — overrides the OpenAI-compatible endpoint for a proxy or gateway. |
| `SAM3_SERVER_URL` | Required only for `segmentation` (self-hosted SAM3 server). |
| `ffmpeg` + `ffprobe` | Required for audio extraction, transcoding, and frame sampling/fitting. |
| `OSS_AK`, `OSS_SK`, `OSS_ENDPOINT`, `OSS_BUCKET` | Optional — upload oversized local video and pass a signed URL instead of local frame sampling. Install the `oss` extra as well. |

Set variables in the environment or `~/.freeglm/config`. The guided installer can write the
shared configuration and verify the system dependencies:

```bash
bash install.sh configure
bash install.sh verify
```

The default Omni model is `qwen3.5-omni-plus`; pass `model` to an individual tool to override it.

---

## Video delivery and OSS

Both video paths — `vision_chat` and the Omni tools — use the same switch: **if OSS is fully
configured, the local video is uploaded and a signed URL is passed to the model for server-side
sampling; otherwise it falls back to local frame extraction.** Configuring OSS lifts the local inline
limits (250 frames / ~40 minutes for `vision_chat`) and lets the server sample long inputs — up to the
model's server-side video-duration cap (e.g. qwen3.7-plus 2 h, Qwen3.5-Omni 1 h). A local file longer
than that cap skips the upload and degrades to local frame sampling (VL: frames; Omni: frames + audio)
— sparse for very long clips, but it still returns a result.

Without OSS:

- `vision_chat` samples frames locally, bounded by the 250-frame / ~40-minute inline limit; for longer
  videos use core's `read_video` or `video-memory`.
- The Omni tools fit one inline media item to the 10 MB base64 limit: audio that fits is sent
  unchanged, otherwise it is downmixed to 16 kHz mono (duration-fitted MP3 when needed); a short video
  is resized/transcoded to fit; a larger video falls back to sampled frames plus the full audio track,
  thinning frames until the request fits.
- An HTTP(S)/OSS URL is always fetched server-side and skips the local inline path.

`dry_run=true` never triggers a network upload — the OSS branch is shown as a placeholder.

---

## Example requests

```text
@receipt.jpg
OCR this receipt and total the line items.

@street.jpg
Draw a box around every car in the scene.

@meeting.mp4
Transcribe this meeting with speaker labels and sentence-level timestamps. Return SRT.

@demo.mp4
Describe the clip over time, then locate every segment where the presenter opens the settings panel.

@workout.mp4
Count every completed push-up and list the timestamp of each repetition.

@track.wav
Analyze the genre, moods, instruments, key, time signature, and vocal profile. Also write a compact
English caption that could be used as a music-generation prompt.
```

The tools work the same in Chinese — the prompt language mainly steers the wording of the answer:

```text
@会议录音.m4a
把这段录音转成文字，不需要时间戳。

@访谈.mp4
区分说话人并逐句标注时间，输出 SRT 字幕。

@产品演示.mp4
按时间顺序描述视频内容，并找出讲解人第一次展示价格页面的时间段。

@监控.mp4
数一下画面里一共出现了几辆电动车，并列出每次出现的时间点。

@片头音乐.mp3
分析这首曲子的风格、情绪、乐器、调性和节拍，再写一段可用于音乐生成的英文提示词。
```

---

## Cases

No case recorded yet. Add one in either style — see [core](../core/usage.md) for worked examples:

- **Trace** — a full session rendered to a self-contained HTML page, linked by URL.
- **Result** — the query plus a public link to the produced artifact and/or a preview screenshot.
