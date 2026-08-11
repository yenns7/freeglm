# Provider and API setup

**English** · [中文](../zh/provider-setup.md)

This guide explains how to connect Zhipu GLM, Alibaba Cloud Model Studio (DashScope), Serper, and how to distinguish “a setting exists” from “the feature works.” If “GIM API” refers to this project's vision backend, its correct name is the **GLM API**.

## Choose the smallest capability first

| Goal | Capability | Provider / configuration |
|---|---|---|
| Read local images, videos, and documents | `freeglm-core` | No API key |
| VQA, OCR, grounding | `freeglm-api` | Either Zhipu GLM or DashScope |
| Omni A/V, dedicated ASR, generation, video-memory builds | Corresponding `api` / `video-edit` / `video-memory` capability | DashScope; a GLM key is not a substitute |
| Web search, extraction, reverse-image search | `freeglm-search` | Serper |
| SAM3 segmentation / self-hosted ASR | `freeglm-api` | A self-hosted service URL |

At first principles, onboarding has four parts: install the tool, make the credential available to the process, identify the provider that will receive data, and run one real small acceptance request. A line in a config file does not prove that the endpoint, key, model, network, and quota all work together.

## Credential safety

- Never paste a key into chat, an agent prompt, an MCP argument, source code, screenshots, or command-line arguments.
- Do not run commands that print keys, and do not commit a real key in an `.env` file.
- Prefer `bash install.sh configure`. It uses hidden input and writes `~/.freeglm/config` with mode `0600`; environment variables still take precedence.
- `--check-system` and `bash install.sh verify` report only `set` / `not set` and the source, never a key fragment.
- If exposure is suspected, revoke the old key in the provider console, create a replacement, and update local configuration. Editing a local file cannot invalidate an exposed key.

## Zhipu GLM: shortest setup path

Zhipu currently documents GLM-4.6V-Flash as the free version of GLM-4.6V. Its official onboarding flow is to sign in, create an API key, and use the general OpenAI-compatible endpoint `https://open.bigmodel.cn/api/paas/v4/`; FreeGLM uses `glm-4.6v-flash` by default. Free availability is governed by Zhipu's current policy. Follow the official [Zhipu HTTP API guide](https://docs.bigmodel.cn/cn/guide/develop/http/introduction) and [GLM-4.6V-Flash model guide](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.6v-flash).

1. Install `freeglm-api`, or run the guided installer from a checkout.
2. Run `bash install.sh configure`.
3. Open **Credentials & endpoints**, choose `ZHIPU_API_KEY`, and paste the key into the hidden prompt.
4. Normally keep the default `ZHIPU_BASE_URL` and `ZHIPU_VISION_MODEL=glm-4.6v-flash`. Change the endpoint only when a trusted proxy or organizational gateway requires it; the endpoint and credential must belong to the same trusted service.
5. Return to the main menu, run **Verify**, and select `freeglm-api`.

For an offline source-checkout check:

```bash
python3 scripts/check_security_contract.py
uvx --from ".[api]" freeglm-api --check-system
```

`vision_chat`, `ocr`, and `grounding` accept `provider="zhipu"`. With only `ZHIPU_API_KEY`, automatic routing selects Zhipu. If a DashScope key also exists, automatic routing defaults to DashScope, so explicitly select `provider="zhipu"` when GLM is required.

Video behavior: a provider-reachable remote video URL uses GLM's native `video_url`; a local video uses a configured OSS signed URL, or falls back to locally sampled image frames when OSS is absent. `dry_run=true` never uploads. Before private media leaves the machine, confirm that sending it to Zhipu or the configured OSS is within the user's consent.

### Live Zhipu acceptance

The live checks generate a small test image and call the real API. They can consume free quota or incur cost and never print the key. After explicit authorization to use the account, run:

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k zhipu tests/test_api_reachability.py
```

Then perform three agent-level checks:

```text
Describe this test image in one sentence, explicitly using provider=zhipu.
Recognize the text in this test image, explicitly using provider=zhipu.
Locate the colored regions in this test image and return boxes, explicitly using provider=zhipu.
```

## DashScope: vision and broader media services

Create a key in [Alibaba Cloud Model Studio](https://help.aliyun.com/zh/model-studio/get-api-key/). The key, base URL, region, and billing plan must match; a cross-region mismatch commonly appears as a 401. Use the official [Base URL guide](https://help.aliyun.com/en/model-studio/base-url) and [region guide](https://help.aliyun.com/zh/model-studio/regions/).

Run `bash install.sh configure`, then set `DASHSCOPE_API_KEY` under **Credentials & endpoints**. Change `DASHSCOPE_BASE_URL` only when required for the chosen region. Then run:

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra api pytest -m reachability -k dashscope tests/test_api_reachability.py
```

GLM currently covers only `vision_chat` / `ocr` / `grounding`; `transcribe_audio`, Omni, generation, and video-memory construction retain their documented DashScope or self-hosted service requirements.

## Serper: search capabilities

Create a key in the [Serper](https://serper.dev/) dashboard, then set `SERPER_API_KEY` through `bash install.sh configure`. Validate it with:

```bash
FREEGLM_RUN_REACHABILITY=1 uv run --with pytest --extra search pytest -m reachability -k serper tests/test_api_reachability.py
```

`web_search` and `web_extractor` send queries or URLs to external services. Reverse-searching a local image also uploads it to the documented third-party public image host, so explicit consent is required immediately before each upload; confidential images should not use that path.

## Layered validation: installed to usable

| Layer | What it proves | Recommended check |
|---|---|---|
| Configuration | Required names exist, source is known, value stays hidden | `bash install.sh verify` or `<entry> --check-system` |
| Discovery | Skill and MCP server are active in the current agent | Inspect the live skill/tool inventory and find the intended tool |
| Offline contract | Schema, routing, redaction, media fallbacks, MCP protocol | `uv run --with pytest --extra all pytest -m "not reachability" tests/` |
| Live reachability | Key, endpoint, model, network, and account quota | The opt-in reachability checks above |
| Business acceptance | Quality, privacy, and cost fit the real task | One minimal non-sensitive agent task |

Live tests are skipped by default even when credentials exist. They send requests only when `FREEGLM_RUN_REACHABILITY=1` is set.

## Troubleshooting

| Symptom | Check first |
|---|---|
| `no API key` | Correct variable name; whether the process can read `~/.freeglm/config`; whether an empty environment value shadows file configuration |
| 401 / authentication failure | Revoked key; base URL, region, and plan mismatch; a key paired with the wrong provider endpoint |
| 404 / model not found | Model availability for this account; restore `glm-4.6v-flash` or the provider's documented model name |
| 429 | Quota, concurrency, and rate limits; reduce concurrency and inspect the provider console |
| Timeout | Network, media size, and `FREEGLM_CHAT_TIMEOUT`; retry a small image to separate account from media issues |
| GLM configured but DashScope selected | With both keys, `auto` defaults to DashScope; explicitly set `provider="zhipu"` |
| Agent cannot see the tool | The skill/MCP is not installed in this harness, or its tool inventory needs a restart/refresh |
| Local video fails | Check `ffmpeg` / `ffprobe`; for native video input, fully configure OSS or provide a provider-reachable URL |

For Zhipu HTTP and business errors, use the official [API error-code guide](https://docs.bigmodel.cn/cn/faq/api-code). Logs and returned errors must remain redacted; do not print request headers, signed URLs, or config-file contents to debug them.

## Rotate or remove a key

1. Create a new key or revoke the old key in the provider console.
2. Run `bash install.sh configure` and select the field; entering `-` clears its local config value.
3. If an environment variable also held the old key, update or remove it in the trusted secret store that launches the agent.
4. Restart the agent/MCP server, then repeat the configuration check and one minimal live acceptance test.

## Maintainers: add a provider or model

Complete every layer; adding one environment variable is not an integration:

1. Register fields in both `src/shared/env.py` `CONFIG_FIELDS` and `install.sh` `CONFIG_SPEC`, with the correct secret flag.
2. Implement explicit provider selection and safe defaults in a shared resolver. Public MCP schemas may expose a non-sensitive `provider` selector, but never `api_key`, `base_url`, tokens, or secrets.
3. Verify the real image/video/audio wire formats. Use a conservative fallback for unknown behavior; do not claim a provider lacks a feature based on stale assumptions.
4. Update tool descriptions, agent routing, data-egress documentation, and this guide.
5. Add offline unit tests plus reachability tests guarded by both a credential and explicit opt-in.
6. If a capability or entry point changes, synchronize manifests and run `python3 scripts/check_manifests.py`. See [adding a capability](how_to_add_new_capability.md) for the complete directory workflow.
7. Before merging, run the security contract, full offline suite, Ruff, and `git diff --check`. Never put a real key in a fixture or example.
