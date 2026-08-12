---
name: freeglm-search
description: Web and reverse-image search MCP tools (Serper) for confirming facts — web_search (find facts), web_extractor (read a page in depth), image_search (reverse-search a frame to identify an entity). Reverse-searching a local image requires explicit user consent because it is uploaded to a third-party public host; prefer an already-public URL. Use to verify anything you cannot confirm from the media alone.
---

# FreeGLM Search

You have `freeglm-search` MCP tools available. They call the Serper API to look things up on the web. Needs `SERPER_API_KEY`.

The key comes only from the user's environment or `~/.freeglm/config`; never ask for it in chat or
put it in a tool argument. A local `image_search` upload leaves the machine and becomes publicly
accessible on a third-party host, so obtain explicit consent and prefer an already-public URL.

Check the `freeglm-search` tools in your tool list for full schemas and parameters.

## When to Use Which Tool

- **Search the web** for facts → `web_search`
- **Read a web page** in depth → `web_extractor`
- **Reverse image search** to identify an entity from a frame/photo → `image_search`

## Confirm Before You Commit

Any question that needs external knowledge — identifying a specific thing, OR a fact about what's shown that you cannot confirm from the media alone — MUST be confirmed with a search before you answer. Never commit from appearance alone.

Typical flow (spans capabilities):
1. Watch the video with `freeglm-core`'s `read_video` — for a long video do a low-fps overview first (~32 frames, `fps≈32/duration`), then zoom. Don't run `ffmpeg`/montage yourself.
2. Grab the frame to search with core's `save_view` (`times=[...]`).
3. `image_search` (reverse-search the frame) and/or `web_search` to confirm the identity/fact.
4. Optionally cross-check appearance with `freeglm-api`'s `vision_chat`.

Details and worked examples in `references/video_search.md`.

## Relationship to Other Capabilities

- **Frames come from** `freeglm-core` (`save_view` / `read_video`) — this capability does not read media.
- **Model-based understanding** (caption, OCR, grounding, ASR) → `freeglm-api`.
