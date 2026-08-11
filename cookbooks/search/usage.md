# Cookbook — FreeGLM Search

`freeglm-search` confirms facts with the Serper API — web search, page extraction, and reverse
image search. Use it whenever a question about what's on screen needs outside knowledge (what is
this place / this building / this person?) that the media itself can't confirm.

For local reading of the media first, see [`core`](../core/usage.md); for model-based captioning /
grounding of the same image, see [`api`](../api/usage.md).

---

## Tools

- `web_search` — find facts on the web (query + optional site filter).
- `web_extractor` — read one page in depth (URL in, extracted content out).
- `image_search` — reverse-image search a local file or URL to identify an entity.

Needs `SERPER_API_KEY` (in the environment or `~/.freeglm/config`).

## Typical flow

1. Read / watch the media with `freeglm-core` (`read_image` / `read_video`).
2. Grab the frame to search with core's `save_view` (`times=[...]`).
3. `image_search` (reverse-search the frame) and/or `web_search` to confirm the identity / fact.
4. Cross-check appearance with `freeglm-api`'s `vision_chat` when helpful.

**Rule: never commit from appearance alone** — if you can't confirm the fact from the media
itself, confirm it with a search first.

## Example

```text
@place.jpg   Where was this photo taken?        # image_search + web_search
```
