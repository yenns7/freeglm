# FreeGLM project map

This page is the central ownership and applicability map. It documents responsibilities once at the
capability or directory boundary; individual files should carry extra prose only when they expose a
public contract, implement a non-obvious algorithm, or contain copied/vendored material that needs
specific provenance.

## Capability catalog

| Capability | Use it for | Do not treat it as | Runtime and composition boundary |
|---|---|---|---|
| `freeglm-core` | Local image/video reading, media metadata, supported file visualization, crop, bounding-box annotation, saved frames | Cloud OCR/VQA/grounding, arbitrary unsupported file formats, whole-video semantic memory | Local MCP server; optional system renderers. Compose with `api` for external understanding and `video-memory` for long-video QA |
| `freeglm-api` | External VQA, OCR, spatial grounding, Omni A/V tasks, dedicated ASR, SAM3 segmentation | Local file viewer, web fact verification, long-video memory | Networked services. GLM covers only `vision_chat`/`ocr`/`grounding`; other families keep their documented service requirements |
| `freeglm-search` | Web facts, page extraction, reverse-image verification | A media reader or proof based on appearance alone | Serper/network required. A local reverse-search image leaves the machine and requires explicit consent |
| `freeglm-video-memory` | Whole-video QA and semantic navigation for videos of 30 minutes or more, including directories of long videos | Frame-accurate visual evidence or the default path for every short clip | Building memory writes `<video>.memory/` and calls external services; re-open a narrow interval with `core` before frame-level claims |
| `freeglm-video-edit` | Editing supplied real footage; image/video/audio generation tools included with the capability | General video QA or a replacement for source inspection | Editing skill owns the timeline; use `core` for perception, `api` only for requested external analysis, and `video-memory` only for long-source navigation |
| `freeglm-blender` | Blender scene/asset creation, refinement, materials, lighting, rendering | Parametric engineering CAD | Thin client to a live Blender + addon; asset search/download and generation tools may contact external providers |
| `freeglm-freecad` | Parametric parts/assemblies, technical exports, parts library, FEM/CalculiX | Artistic mesh modeling or a general-purpose renderer | Thin client to a live FreeCAD + addon; FEM additionally needs CalculiX |
| `freeglm-edu-agent` | Step-by-step Chinese math and supported K-12 science explainer videos/pages from text or problem images | A general presentation generator or an MCP server | Skill-only; uses Node/HyperFrames/Chromium/ffmpeg and sends narration text to DashScope TTS |
| `freeglm-example` | Developer template for a new capability | A production capability to install from the marketplace | Not listed in the marketplace; its demo API call may contact a configured OpenAI-compatible endpoint |

## Repository responsibilities

| Path | Responsibility | Maintenance rule |
|---|---|---|
| `src/capabilities/<name>/skill/` | Agent routing, workflow, safety and quality gates for one capability | `SKILL.md` frontmatter describes triggers and exclusions; it must not claim tools owned by another capability |
| `src/capabilities/<name>/freeglm_<name>/` | MCP server implementation for one capability | Tool schemas are the executable source of truth for parameters and side effects |
| `src/shared/` | Cross-capability environment, media, content, retry, cache, OSS and provider helpers | Keep provider-neutral logic here; do not make one capability import a sibling server package |
| `src/mcp_framework.py` | Tool discovery, schema normalization, server transport, startup/system checks | Shared infrastructure only; no capability-specific marketing claims |
| `.claude-plugin/`, `.zcode-plugin/`, per-capability plugin directories | Marketplace and harness registration | Descriptions must be generated from or checked against capability ownership; manifests do not redefine tool ownership |
| `cookbooks/` | Worked examples and observed workflows | Examples must disclose network, credential and data-egress prerequisites |
| `docs/en/`, `docs/zh/` | Installation, development, routing and architecture guidance | English and Chinese policies must remain semantically aligned |
| `docs/*/provider-setup.md` | End-user provider onboarding, live acceptance, credential rotation, and provider-extension checklist | Keep current against official provider contracts and never include credential-value examples |
| `tests/` | Offline contracts plus credential-gated reachability checks | A skipped live test is not evidence that an external service passed |
| `NOTICE`, `UPSTREAM.md`, capability `NOTICE.md` files | Upstream and vendored-code provenance | Record exact source revisions and preserve required notices |

## Root and control files

This table answers “what is this file for?” for the repository entry points and policy controls. It is
intentionally centralized here so the same explanation is not copied into every file.

| File or group | Responsibility and when it applies | Maintenance boundary |
|---|---|---|
| `README.md` | Primary English landing page, supported capability summary, installation entry points, and safe first-run routing | Keep concise; link to this catalog for detailed ownership and exclusions |
| `README.zh.md` | Chinese counterpart to `README.md` | Keep policy and capability claims semantically aligned with the English page |
| `docs/*/provider-setup.md` | Bilingual GLM, DashScope, and Serper setup and validation entry point | Link from landing, installation, routing, and testing docs; preserve the credential boundary |
| `install.sh` | Interactive source-checkout installer, profile selection, harness registration, system checks, and hidden credential configuration | Operational entry point; it must not print secrets or imply that every optional dependency is installed |
| `.env.example` | Inventory of recognized configuration names and non-secret defaults | Documentation only; never store credential values or instruct users to expose them in chat or command output |
| `pyproject.toml` | Python distribution metadata, dependency profiles, console entry points, package layout, and test configuration | Packaging source of truth; capability applicability stays in this catalog and each capability's tool/skill contract |
| `CLAUDE.md` / `AGENTS.md` | Agent-harness operating instructions and repository contribution constraints | Apply only in the harnesses/scopes that load them; they do not add runtime capabilities |
| `SECURITY.md` | Vulnerability reporting, credential-handling policy, and data-egress security boundary | Security policy, not an installation guide; reports must be scrubbed of secrets and private media |
| `CONTRIBUTING.md` | Contributor setup, change workflow, validation expectations, and pull-request guidance | Applies to repository changes, not end-user capability routing |
| `LICENSE` / `NOTICE` / `UPSTREAM.md` | Project license, required third-party notices, and the exact imported upstream baseline and relationship | Preserve required text; update `UPSTREAM.md` with an immutable revision when importing upstream changes |
| `scripts/check_manifests.py` | Checks capability registration and generated manifest consistency | Run after capability, plugin, entry-point, or marketplace metadata changes |
| `scripts/check_security_contract.py` | Checks repository-wide secret-handling and security documentation contracts | Run after installer, configuration, credential, logging, tool-schema, or security-policy changes |
| `scripts/gen_env_docs.py` | Generates or validates environment-variable documentation from the maintained configuration definitions | Run after adding, renaming, or removing recognized configuration names; do not hand-copy the inventory into many docs |
| Vendored code (`**/vendor/`) | Third-party source retained for runtime integration | Govern by the nearest notice/license and preserve provenance; do not rewrite it to match local style. A provider-published shared trial identifier in the Blender vendor tree is public, quota-limited vendor data—not a user secret—and must never be replaced with a private credential |
| Assets (`**/assets/`) | Shipped visual, font, fixture, or template resources owned by their containing capability | Document provenance and reuse rules at the directory/catalog level; avoid one descriptive comment per asset |
| Generated files and build outputs | Material produced by repository generators, packaging, tests, or user workflows | Regenerate from the owning source; do not edit or annotate each generated file unless its format explicitly requires it |

## Network, data egress, and credentials

| Capability/path | What can leave the machine | Destination/boundary |
|---|---|---|
| `core` | A URL supplied to a URL-aware renderer is fetched; local-file operations otherwise remain local | Target URL and any external renderer explicitly invoked by the workflow |
| `api` | Prompts, images, sampled frames, audio, or video; oversized media may be uploaded to user-configured OSS | Configured DashScope, Zhipu, SAM3/ASR service, or OSS endpoint |
| `search` | Search queries and requested URLs; a local reverse-search image is uploaded after explicit consent | Serper, target web servers, and the documented third-party public image host |
| `video-memory` | Video clips/frames, audio/ASR content, and generated semantic summaries during memory construction | DashScope and optional user-configured OSS |
| `video-edit` / `edu-agent` | Generation prompts, source media accepted by a selected generation service, or narration text | The selected DashScope generation/TTS service |
| `blender` / `freecad` | Live-app commands normally stay local; optional search, download, generation, or auto-install paths use their documented sources | Local addon plus any explicitly selected external asset/provider endpoint |

Credentials are configuration, never task content:

- Supply them only through the process environment or the private `~/.freeglm/config` file.
- Never paste them into chat, prompts, issue reports, logs, source files, command output, or tool arguments.
- An agent may test whether a credential exists but must not read, print, echo, summarize, or transmit its value.
- Ask for explicit consent before any operation that makes local/private media public or sends it to a
  provider not already implied by the user's request.

## Source of truth order

When descriptions disagree, resolve them in this order:

1. Executable tool schema and implementation for actual parameters and side effects.
2. Capability `SKILL.md` for trigger, workflow, and composition policy.
3. This catalog for ownership and high-level applicability.
4. Marketplace copy and cookbooks for discovery and examples.

Fix the higher-level copy after verifying the executable behavior; do not duplicate a corrective
paragraph into every file.
