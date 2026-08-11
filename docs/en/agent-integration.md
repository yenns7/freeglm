# Agent integration and routing

Use this policy after installing the required FreeGLM capabilities. A capability being present on
disk is not proof that its skill or MCP server is active: inspect the live skill/tool inventory before
planning calls, and report a missing capability instead of pretending that it ran.

## Route by task ownership

| User intent | Primary capability | Compose when needed |
|---|---|---|
| Read an image or short video; inspect metadata; visualize a supported local file | `freeglm-core` | Add `api` only for external-model understanding; add `search` only for external facts |
| OCR, caption/VQA, object grounding, Omni A/V, ASR, segmentation | `freeglm-api` | Use `core` to inspect local evidence and annotate returned boxes |
| Verify an identity or external fact | `freeglm-search` | Use `core/save_view` to select evidence; local reverse search requires explicit upload consent |
| Whole-video QA for one or more videos at least 30 minutes long | `freeglm-video-memory` | After locating an interval, use `core/read_video` on that narrow interval |
| Edit supplied real footage | `freeglm-video-edit` | `core` for source review; `api` for requested model analysis; `video-memory` only for long-source navigation |
| Generate an image, video, or voice asset for an edit | Generation tools installed with `freeglm-video-edit` | Verify the generated asset before timeline integration |
| Create/refine a Blender scene | `freeglm-blender` | Confirm the live Blender/addon connection; inspect rendered evidence |
| Create parametric CAD or run FEM | `freeglm-freecad` | Confirm live FreeCAD/addon; FEM additionally requires CalculiX |
| Produce a Chinese math or supported K-12 science tutorial video/page | `freeglm-edu-agent` | Skill-only workflow; use its declared HyperFrames, browser, ffmpeg, and TTS prerequisites |

## Video decision boundary

1. For video editing, `freeglm-video-edit` owns the workflow regardless of duration.
2. For content QA below 30 minutes, inspect with `freeglm-core`; zoom into relevant windows rather
   than treating sparse thumbnails as complete evidence.
3. For whole-video QA at 30 minutes or more, build/query `freeglm-video-memory` first.
4. Memory is a coarse semantic index. Before claiming a visual detail, re-read the original video in
   a narrow time window with `freeglm-core`.
5. Use `freeglm-search` only when the answer needs outside knowledge, not merely because a frame is
   difficult to see.

## Provider routing

- `vision_chat`, `ocr`, and `grounding` support DashScope Qwen and Zhipu GLM.
- Automatic VL routing chooses Zhipu only when `ZHIPU_API_KEY` is configured and
  `DASHSCOPE_API_KEY` is not. Otherwise it defaults to DashScope unless the provider is selected
  explicitly.
- This is a configuration rule, not a price, speed, or quality comparison.
- Omni A/V, dedicated ASR, segmentation, generation, search, and memory construction keep their own
  documented provider requirements. A GLM credential does not enable those services.
- Use request-preview or dry-run behavior only where the live tool schema advertises it and only when
  previewing has a concrete diagnostic purpose. It is not a universal workflow step.

For exact setup steps, live acceptance commands, video behavior, and provider-specific failure
diagnosis, see [provider and API setup](provider-setup.md).

## Multi-agent coordination

A lead agent remains accountable for the task, final answer, and shared state.

Delegate only when work can be divided into independent, bounded outputs, such as separate source
reviews, non-overlapping capability audits, or distinct assets. Before dispatching, assign each agent:

- a precise objective and completion test;
- a non-overlapping set of files or artifacts;
- the allowed external services and data boundary;
- the evidence it must return; and
- an instruction not to publish, delete, or overwrite shared state outside that scope.

Do not delegate a tightly coupled one-file edit, a decision that needs one coherent judgment, or work
whose agents would write the same files. Parallel agents must not independently produce competing
final answers. The lead agent reviews returned evidence, resolves inconsistencies, runs integration
checks, and communicates one result.

For long-video directories, parallelism may be used for independent per-video memory builds when the
runtime and service limits permit it. Keep output directories separate, record which source produced
each memory, and merge only after every build is attributable and complete.

## Credentials and private data

- Credentials come only from the process environment or private `~/.freeglm/config` file.
- Never ask the user to paste a credential into chat. Never pass credentials in MCP/tool arguments,
  prompts, source files, shell output, logs, screenshots, or agent-to-agent messages.
- Do not inspect or display credential values. A presence/absence check is the maximum an agent needs.
- Do not place credentials in a delegated task. Every worker inherits only the securely configured
  runtime it needs.
- Before sending private media to an external provider, state the destination and obtain consent when
  that transfer is not already clear from the user's request.
- Reverse-searching a local image makes a copy publicly reachable on the documented third-party host;
  explicit consent is mandatory immediately before that operation.

## Failure and fallback

If the owning capability is unavailable, state what is missing and what accuracy or privacy property
would change under a fallback. Do not silently replace a configured provider, external service,
long-video memory workflow, or visual inspection step. Ask before a fallback materially changes data
egress, quality, cost exposure, or the requested output.
