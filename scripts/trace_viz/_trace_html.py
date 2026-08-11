"""Shared trace → HTML rendering for the per-harness session visualizers.

Each harness (`claude_session_viz.py`, `codex_session_viz.py`, …) only has to parse its own
session format into a normalized `conversation` and hand it here; this module owns the HTML so
every cookbook trace looks the same regardless of which harness produced it.

Normalized shape expected by `render_html`:

    conversation = [ turn, … ]                       # in display order
    turn = {
        "user_text": str,                            # the user prompt ("" if none)
        "blocks": [ block, … ],                      # assistant side, in order
        "results": { call_id: result },              # tool outputs, keyed by the call's id
    }
    block = {"kind": "text",     "text": str}
          | {"kind": "thinking", "text": str}
          | {"kind": "tool",     "name": str, "id": call_id, "input": dict|str}
    result = {"content": [ item, … ], "is_error": bool}
    item   = {"type": "text",  "text": str}
           | {"type": "image", "source": {"media_type": str, "data": <base64>}}

That `item` shape is the Claude tool_result shape; harness parsers normalize into it (e.g. Codex's
`input_image` data URLs are split into media_type + base64). Text markers a reader tool emits right
before an image (`<mm:ss>` frame timestamps) become that image's caption; everything else is prose.
"""

from __future__ import annotations

import html as html_mod
import json
import re
from pathlib import Path

# Frame timestamps (read_video emits one `<mm:ss>` marker per frame) are the ONLY text folded away:
# there are hundreds and they're pure per-frame labels, so each becomes its frame's caption.
# EVERYTHING else — including bracketed headers like `[Page 7 View] 1728x1216 (HxW)` — is shown
# verbatim, so we never drop content from tools whose marker format we don't specifically know.
_LABEL_TS = re.compile(r"^<\d+:\d[\d.]*>$")


def label_of(text: str) -> str | None:
    """Return a caption for a bare `<mm:ss>` frame timestamp, else None (text is kept as prose)."""
    t = text.strip()
    return t.strip("<>") if _LABEL_TS.match(t) else None


# Absolute local paths are noise (and can leak usernames) in a published trace, so by default we
# collapse the directory to `/path/to/`, keeping the filename: `/Users/me/Downloads/cakes.png` →
# `/path/to/cakes.png`. The lookbehind avoids URLs (`…github.io/x/y`) and base64 (`+AA/BB`).
_REDACT = True
_PATH_RE = re.compile(r"(?<![:\w/])(/(?:[\w.\-]+/)+[\w.\-]+)")


def redact_paths(text: str) -> str:
    if not _REDACT or not text:
        return text
    return _PATH_RE.sub(lambda m: "/path/to/" + m.group(1).rsplit("/", 1)[-1], text)


def short_tool_name(name: str) -> str:
    return name.split("__")[-1] if "__" in name else name


def tool_summary(name: str, inp) -> str:
    """A compact one-line description of a tool call's input (dict or raw string)."""
    if isinstance(inp, str):
        first = next((ln for ln in inp.splitlines() if ln.strip()), "")
        return first.strip()[:100]
    if not isinstance(inp, dict):
        return ""
    n = short_tool_name(name)
    if n == "Bash":
        return inp.get("description") or (inp.get("command", "").splitlines() or [""])[0][:100]
    for key in ("file_path", "image_path", "video_path", "pdf_path", "path"):
        if inp.get(key):
            return Path(str(inp[key])).name
    if n == "WebSearch":
        return inp.get("query", "")[:100]
    if n == "WebFetch":
        return inp.get("url", "")[:100]
    if inp.get("prompt"):
        return str(inp["prompt"])[:100]
    if inp.get("query"):
        return str(inp["query"])[:100]
    for v in inp.values():
        if isinstance(v, (str, int, float)) and len(str(v)) <= 100:
            return str(v)
    return ""


def clip(text: str, max_output: int | None) -> str:
    """Return text as-is (tool results are kept complete) unless a cap is set."""
    if max_output and len(text) > max_output:
        return text[:max_output] + "\n… (truncated)"
    return text


def sample_evenly(items: list, n: int) -> list:
    """Pick up to n items spread evenly across the list (n<=0 → all). For big frame sets."""
    if n <= 0 or len(items) <= n:
        return list(items)
    if n == 1:
        return [items[0]]
    idx = [round(i * (len(items) - 1) / (n - 1)) for i in range(n)]
    return [items[i] for i in dict.fromkeys(idx)]


# ── Markdown → HTML (for the message bubbles) ─────────────────────────────

def esc(s: str) -> str:
    return html_mod.escape(s)


def _md_inline_html(t: str) -> str:
    """Inline markdown → HTML on an already-escaped string."""
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t


def md_to_html(text: str) -> str:
    """Small block-level markdown → HTML (headings, tables, lists, quotes, code, inline)."""
    if not text:
        return ""
    lines = esc(redact_paths(text)).split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    sep = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre class='md'><code>" + "\n".join(buf) + "</code></pre>")
        elif (m := re.match(r"(#{1,6})\s+(.*)", line)):
            lvl = min(len(m.group(1)) + 1, 6)
            out.append(f"<h{lvl}>{_md_inline_html(m.group(2))}</h{lvl}>")
            i += 1
        elif "|" in line and i + 1 < n and "-" in lines[i + 1] and sep.match(lines[i + 1]):
            head = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{_md_inline_html(c)}</th>" for c in head)
            body = "".join("<tr>" + "".join(f"<td>{_md_inline_html(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>")
        elif line.lstrip().startswith("&gt;"):
            buf = []
            while i < n and lines[i].lstrip().startswith("&gt;"):
                buf.append(re.sub(r"^\s*&gt;\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{_md_inline_html('<br>'.join(buf))}</blockquote>")
        elif re.match(r"^\s*[-*]\s+", line):
            buf = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append(_md_inline_html(re.sub(r"^\s*[-*]\s+", "", lines[i])))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in buf) + "</ul>")
        elif re.match(r"^\s*\d+\.\s+", line):
            buf = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append(_md_inline_html(re.sub(r"^\s*\d+\.\s+", "", lines[i])))
                i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in buf) + "</ol>")
        else:
            buf = []
            while i < n and lines[i].strip() and not lines[i].startswith("```") \
                    and not re.match(r"#{1,6}\s|^\s*[-*]\s+|^\s*\d+\.\s+", lines[i]) \
                    and not lines[i].lstrip().startswith("&gt;") \
                    and not ("|" in lines[i] and i + 1 < n and sep.match(lines[i + 1]) and "-" in lines[i + 1]):
                buf.append(lines[i])
                i += 1
            out.append(f"<p>{_md_inline_html('<br>'.join(buf))}</p>")
    return "\n".join(out)


# ── HTML emitter ──────────────────────────────────────────────────────────

def tool_body_html(tr: dict, max_output: int | None, max_images: int) -> str:
    """Render a tool result preserving the original text↔image order.

    Prose text becomes <pre> blocks; runs of consecutive images (each captioned by its preceding
    label) become one horizontal filmstrip.
    """
    cont = tr.get("content", "") if tr else ""
    out_cls = "out err" if (tr and tr.get("is_error")) else "out"
    if not isinstance(cont, list):
        text = redact_paths((cont if isinstance(cont, str) else str(cont)).strip())
        return f'<pre class="{out_cls}">{esc(clip(text, max_output))}</pre>' if text else ""

    parts: list[str] = []
    prose: list[str] = []
    film: list[dict] = []
    pending = ""

    def flush_prose() -> None:
        txt = "\n".join(prose).strip()
        prose.clear()
        if txt:
            parts.append(f'<pre class="{out_cls}">{esc(clip(txt, max_output))}</pre>')

    def flush_film() -> None:
        if not film:
            return
        shown = sample_evenly(film, max_images)
        if len(shown) < len(film):
            note = f'<div class="frames-note">{len(shown)} of {len(film)} frames, sampled evenly</div>'
        elif len(film) > 1:
            note = f'<div class="frames-note">{len(film)} frames — scroll →</div>'
        else:
            note = ""
        figs = ""
        for img in shown:
            cap = esc(img["label"] or "")
            uri = f'data:{img["media_type"]};base64,{img["data"]}'
            figcap = f"<figcaption>{cap}</figcaption>" if cap else ""
            figs += (f'<figure><img loading="lazy" src="{uri}" alt="{cap}" '
                     f'onclick="lb(this.src)">{figcap}</figure>')
        parts.append(f'{note}<div class="strip">{figs}</div>')
        film.clear()

    for it in cont:
        if not isinstance(it, dict):
            continue
        if it.get("type") == "text":
            lab = label_of(it.get("text", ""))
            if lab is not None:
                pending = lab
            elif it.get("text", "").strip():
                flush_film()
                prose.append(redact_paths(it.get("text", "")))
        elif it.get("type") == "image":
            src = it.get("source", {})
            if src.get("data"):
                flush_prose()
                film.append({"media_type": src.get("media_type", "image/png"),
                             "data": src["data"], "label": pending})
            pending = ""
    flush_prose()
    flush_film()
    return "".join(parts)


def tool_args_html(inp) -> str:
    """Render a tool call's arguments as a <pre> (dict → pretty JSON; JSON string → pretty; else raw)."""
    if isinstance(inp, dict):
        txt = json.dumps(inp, indent=2, ensure_ascii=False) if inp else ""
    elif isinstance(inp, str) and inp.strip():
        txt = inp.strip()
        try:
            txt = json.dumps(json.loads(txt), indent=2, ensure_ascii=False)
        except Exception:
            pass  # not JSON (e.g. an exec code snippet) — show verbatim
    else:
        txt = ""
    return f'<pre class="args">{esc(redact_paths(txt))}</pre>' if txt else ""


def render_html(conversation: list[dict], title: str, harness: str, max_output: int | None = None,
                include_thinking: bool = True, max_images: int = 0,
                assistant: str = "Qwen3.8 Max", redact: bool = True) -> str:
    global _REDACT
    _REDACT = redact
    rows: list[str] = []
    for turn in conversation:
        if turn.get("user_text"):
            rows.append(f'<div class="u"><div class="who">User</div>'
                        f'<div class="bubble">{md_to_html(turn["user_text"])}</div></div>')
        for b in turn.get("blocks", []):
            if b["kind"] == "thinking":
                if include_thinking and b["text"].strip():
                    rows.append(f'<details class="think"><summary>💭 Thinking</summary>'
                                f'<div class="bubble">{md_to_html(b["text"].strip())}</div></details>')
            elif b["kind"] == "tool":
                name = esc(short_tool_name(b["name"]))
                summ = esc(redact_paths(tool_summary(b["name"], b.get("input"))))
                args = tool_args_html(b.get("input"))
                body = tool_body_html(turn.get("results", {}).get(b["id"], {}), max_output, max_images)
                rows.append(f'<div class="t"><div class="tline"><span class="tn">{name}</span>'
                            f'<span class="ts">{summ}</span></div>{args}{body}</div>')
            elif b["kind"] == "text" and b["text"].strip():
                rows.append(f'<div class="a"><div class="who">{esc(assistant)}</div>'
                            f'<div class="bubble">{md_to_html(b["text"].strip())}</div></div>')
    body_html = "\n".join(rows)
    return (_HTML.replace("__TITLE__", esc(title))
                 .replace("__TAG__", esc(harness))
                 .replace("__BODY__", body_html))


_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #fbfbfa; color: #1a1a1a;
         font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
  main { max-width: 760px; margin: 0 auto; padding: 48px 24px 96px; }
  h1 { font-size: 18px; font-weight: 600; margin: 0 0 32px; letter-spacing: -0.01em; }
  h1 .tag { display: inline-block; vertical-align: middle; margin-left: 10px;
            font-size: 11px; font-weight: 600; letter-spacing: 0.03em; color: #5b4bdb;
            background: #efeafe; border: 1px solid #ddd4fb; border-radius: 999px;
            padding: 2px 10px; }
  .who { font-size: 11px; font-weight: 600; text-transform: uppercase;
         letter-spacing: 0.06em; color: #8a8a85; margin-bottom: 6px; }
  .u, .a { margin: 24px 0; }
  .bubble { word-wrap: break-word; overflow-wrap: break-word; }
  .u .bubble { color: #111; }
  .a .bubble { color: #333; }
  .bubble p { margin: 0 0 10px; }
  .bubble p:last-child { margin-bottom: 0; }
  .bubble h2 { font-size: 17px; margin: 18px 0 8px; }
  .bubble h3 { font-size: 15px; margin: 16px 0 6px; }
  .bubble h4 { font-size: 14px; margin: 14px 0 6px; color: #444; }
  .bubble ul, .bubble ol { margin: 6px 0 10px; padding-left: 22px; }
  .bubble li { margin: 2px 0; }
  .bubble code { background: #f0f0ec; padding: 1px 5px; border-radius: 4px;
                 font: 12.5px ui-monospace, "SF Mono", Menlo, monospace; }
  .bubble pre.md { background: #f4f4f1; padding: 10px 12px; border-radius: 6px; overflow-x: auto; }
  .bubble pre.md code { background: none; padding: 0; }
  .bubble blockquote { margin: 8px 0; padding: 2px 12px; border-left: 3px solid #d9d9d4;
                       color: #555; }
  .bubble a { color: #5b4bdb; }
  .bubble table { border-collapse: collapse; margin: 10px 0; font-size: 13px; display: block;
                  overflow-x: auto; max-width: 100%; }
  .bubble th, .bubble td { border: 1px solid #e0e0db; padding: 6px 10px; text-align: left;
                           vertical-align: top; }
  .bubble th { background: #f4f4f1; font-weight: 600; }
  .t { margin: 12px 0; padding-left: 14px; border-left: 2px solid #e5e5e0; }
  .tline { display: flex; gap: 8px; align-items: baseline; }
  .tn { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 13px;
        font-weight: 600; color: #5b4bdb; }
  .ts { color: #8a8a85; font-size: 13px; overflow: hidden; text-overflow: ellipsis;
        white-space: nowrap; }
  pre.out { margin: 8px 0 0; padding: 10px 12px; background: #f4f4f1;
            border-radius: 6px; font: 12px/1.5 ui-monospace, "SF Mono", Menlo, monospace;
            white-space: pre-wrap; word-break: break-word; max-height: 320px;
            overflow: auto; color: #444; }
  pre.out.err { background: #fdf0ef; color: #b3261e; }
  pre.args { margin: 8px 0 0; padding: 10px 12px; background: #f3f2fb;
             border: 1px solid #e7e4fb; border-radius: 6px;
             font: 12px/1.5 ui-monospace, "SF Mono", Menlo, monospace;
             white-space: pre-wrap; word-break: break-word; max-height: 300px;
             overflow: auto; color: #444; }
  details.think { margin: 16px 0; }
  details.think > summary { cursor: pointer; color: #8a8a85; font-size: 13px;
                            list-style: none; }
  details.think .bubble { margin-top: 8px; padding-left: 14px; border-left: 2px solid #e5e5e0;
                          color: #666; }
  .frames-note { margin: 8px 0 4px; color: #8a8a85; font-size: 12px; }
  .strip { display: flex; gap: 8px; overflow-x: auto; padding: 4px 0 10px;
           scroll-snap-type: x proximity; -webkit-overflow-scrolling: touch; }
  .strip figure { flex: 0 0 auto; margin: 0; scroll-snap-align: start; text-align: center; }
  .strip img { height: 150px; width: auto; max-width: none; border: 1px solid #e5e5e0;
               border-radius: 6px; cursor: zoom-in; display: block; background: #fff; }
  .strip figcaption { margin-top: 4px; color: #8a8a85; font-size: 11px;
                      font-family: ui-monospace, "SF Mono", Menlo, monospace; }
  .strip::-webkit-scrollbar { height: 8px; }
  .strip::-webkit-scrollbar-thumb { background: #d0d0cc; border-radius: 4px; }
  #lb { display: none; position: fixed; inset: 0; z-index: 100; cursor: zoom-out;
        background: rgba(0,0,0,.85); align-items: center; justify-content: center; }
  #lb.on { display: flex; }
  #lb img { max-width: 94vw; max-height: 94vh; border-radius: 6px; }
</style></head><body><main>
<h1>__TITLE__ <span class="tag">__TAG__</span></h1>
__BODY__
</main>
<div id="lb" onclick="this.classList.remove('on')"><img alt=""></div>
<script>
function lb(src){var d=document.getElementById('lb');d.querySelector('img').src=src;d.classList.add('on');}
document.addEventListener('keydown',function(e){if(e.key==='Escape')document.getElementById('lb').classList.remove('on');});
</script>
</body></html>"""
