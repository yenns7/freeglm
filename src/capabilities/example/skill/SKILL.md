---
name: freeglm-example
description: Example/template capability — a minimal MCP server whose demo tools (echo, make_swatch, make_film_strip, describe, config_probe) show how a FreeGLM capability is structured: the content-return shapes, calling an API, reading env/config, and composing other capabilities. Use it as the starting point when adding a new capability.
---

# Example Capability (template)

A minimal reference capability. To start a new one, copy `capabilities/example/` and adapt it —
see the repo's *how to add a new capability* doc for the full walkthrough.

You have the `freeglm-example` MCP tools available:

- **echo** — return text (a text-only tool).
- **make_swatch** — generate a solid-color image (an image return, built with `shared.content.image`).
- **make_film_strip** — generate N frames as images (the multi-frame / video pattern).
- **describe** — ask an OpenAI-compatible chat model, optionally about a local image (an API-calling
  tool; pass `dry_run=true` to see the request without a key or network).
- **config_probe** — report how config resolves via `shared.env.get_env` (env / config / default).

Check the tools in your tool list for full schemas. They exist to demonstrate the building blocks a
real capability uses — content-return shapes, an API call, and env/config access.

## Environment & config

Config is read via **`shared.env.get_env(name, default)`**, with precedence
**environment variable > `~/.freeglm/config` > default**. For example, `describe` gets
`DASHSCOPE_API_KEY` this way (through `resolve_openai_endpoint`), and `config_probe` reads the demo
tunable `FREEGLM_EXAMPLE_GREETING`. Run **config_probe** to see what currently resolves.

MCP-server code imports `get_env` from `shared.env` directly. **Skill-side helper scripts run
detached and cannot import `shared`** — so if your skill ships its own scripts, copy the tiny
`env_config.py` mirror (see `video-memory` / `edu-agent`) to get the same precedence.

## Composing other capabilities (dependencies)

A capability should reuse other capabilities rather than reimplement them. This template has **no
media reader of its own**, so:

- If the user gives a **video**, first call **`read_video`** from **`freeglm-core`** to
  extract frames, then feed a frame path to `describe` (to caption it) or `make_swatch`.
- If the user gives a **document / PDF / 3D model**, use `freeglm-core`'s reading tools the
  same way before doing example-specific work.

When your capability depends on another, say so here and name the exact tool to call — that is how a
skill tells the model to compose plugins instead of guessing.
