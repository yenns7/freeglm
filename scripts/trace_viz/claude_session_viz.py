#!/usr/bin/env python3
"""Claude Code session JSONL → a self-contained HTML cookbook trace.

The **Claude Code** visualizer — an authoring helper, run only when adding a trace to a cookbook
(its output HTML is committed next to the capability's `usage.md` and linked from it). `scripts/`
holds one visualizer per harness (`codex_session_viz.py`, …); they parse their own session format
and share the HTML rendering in `_trace_html.py`, so every cookbook trace looks the same.

Point it at **any** Claude Code session `.jsonl` (saved under
`~/.claude/projects/<slug>/<uuid>.jsonl`, or captured with
`claude -p "…" --output-format stream-json > run.jsonl`):

    python3 scripts/trace_viz/claude_session_viz.py <session>.jsonl \\
        --summary "Read a chart" -o cookbooks/core/case-core-read-chart.html

The page is standalone: the model's markdown is rendered, thinking is folded, and every image is
inlined and shown as a horizontal, swipeable filmstrip with click-to-enlarge. All frames are kept
by default. GitHub won't preview an HTML file inline, so link it for download/open.

Usage:
    claude_session_viz.py <session.jsonl> [-o OUT] [--summary TEXT] [--assistant NAME]
                          [--no-thinking] [--max-output N] [--max-images N]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _trace_html import render_html

# ── JSONL parsing (Claude Code session format) ──────────────────────────

def parse_session(jsonl_path: str) -> list[dict]:
    """Return an ordered list of turns; each user turn carries its assistant blocks."""
    lines = []
    with open(jsonl_path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                continue

    # Track parent links for EVERY entry (file-history-snapshot, system, … all carry a uuid and
    # can sit in the parentUuid chain). If we only recorded user/assistant, the walk up to a
    # user turn would dead-end on a non-message parent and silently drop that assistant chain.
    parent_of: dict[str, str | None] = {}
    msg_map: dict[str, dict] = {}
    order: list[str] = []
    for obj in lines:
        uid = obj.get("uuid", "")
        if uid:
            parent_of[uid] = obj.get("parentUuid")
        t = obj.get("type")
        if t not in ("user", "assistant"):
            continue
        msg_map[uid] = {"type": t, "uuid": uid, "parent": obj.get("parentUuid"),
                        "message": obj.get("message", {})}
        order.append(uid)

    user_uuids = {u for u in order if msg_map[u]["type"] == "user"}

    def user_ancestor(uid: str | None) -> str | None:
        seen = set()
        cur = uid
        while cur and cur not in seen:
            if cur in user_uuids:
                return cur
            seen.add(cur)
            cur = parent_of.get(cur)
        return None

    conversation: list[dict] = []
    children: dict[str, list[dict]] = {}
    for uid in order:
        entry = msg_map[uid]
        if entry["type"] == "user":
            conversation.append(entry)
        else:
            parent = user_ancestor(entry["parent"])
            if parent:
                children.setdefault(parent, []).append(entry)

    for turn in conversation:
        content = turn["message"].get("content", [])
        user_text, results = "", {}
        if isinstance(content, list):
            for b in content:
                if b.get("type") == "text":
                    user_text += b.get("text", "")
                elif b.get("type") == "tool_result":
                    results[b.get("tool_use_id", "")] = _norm_result(b)
        elif isinstance(content, str):
            user_text = content
        turn["user_text"] = user_text.strip()
        turn["results"] = results

        blocks: list[dict] = []
        for child in children.get(turn["uuid"], []):
            cc = child["message"].get("content", [])
            if not isinstance(cc, list):
                continue
            for b in cc:
                bt = b.get("type")
                if bt == "thinking":
                    blocks.append({"kind": "thinking", "text": b.get("thinking", "")})
                elif bt == "tool_use":
                    blocks.append({"kind": "tool", "name": b.get("name", ""),
                                   "id": b.get("id", ""), "input": b.get("input", {})})
                elif bt == "text":
                    blocks.append({"kind": "text", "text": b.get("text", "")})
        turn["blocks"] = blocks

    # A tool_use's result lives in the *following* user turn, not the one the tool_use is grouped
    # under — so index every result globally and share the map with all turns.
    global_results: dict[str, dict] = {}
    for turn in conversation:
        global_results.update(turn["results"])
    kept = [t for t in conversation if t["user_text"] or t["blocks"]]
    for t in kept:
        t["results"] = global_results
    return kept


def _norm_result(block: dict) -> dict:
    """Normalize a Claude tool_result into the shared {content:[…], is_error} shape."""
    cont = block.get("content", "")
    items: list[dict] = []
    if isinstance(cont, list):
        for it in cont:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "text":
                items.append({"type": "text", "text": it.get("text", "")})
            elif it.get("type") == "image":
                src = it.get("source", {})
                items.append({"type": "image", "source": {
                    "media_type": src.get("media_type", "image/png"), "data": src.get("data", "")}})
    elif isinstance(cont, str):
        items.append({"type": "text", "text": cont})
    return {"content": items, "is_error": bool(block.get("is_error"))}


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Render a Claude Code session JSONL as a self-contained HTML trace.")
    ap.add_argument("jsonl", help="path to the session .jsonl")
    ap.add_argument("-o", "--output", help="output HTML file (default: <session>.html in cwd)")
    ap.add_argument("--summary", help="page title (default: 'Session trace')")
    ap.add_argument("--assistant", default="Qwen3.8 Max",
                    help='label for the assistant role (default: "Qwen3.8 Max")')
    ap.add_argument("--no-thinking", action="store_true",
                    help="omit thinking blocks entirely (default: include them, collapsed)")
    ap.add_argument("--max-output", type=int, default=None,
                    help="cap each tool result to N chars (default: keep results complete)")
    ap.add_argument("--max-images", type=int, default=0,
                    help="max images per tool result, sampled evenly "
                         "(default: 0 = keep all, shown as a scrollable filmstrip)")
    ap.add_argument("--keep-paths", action="store_true",
                    help="keep absolute local paths (default: redact to /path/to/<name>)")
    args = ap.parse_args()

    if not Path(args.jsonl).exists():
        ap.error(f"file not found: {args.jsonl}")
    conversation = parse_session(args.jsonl)
    if not conversation:
        ap.error("no user/assistant turns found — is this a Claude Code session JSONL?")

    out_file = Path(args.output) if args.output else Path(Path(args.jsonl).with_suffix(".html").name)
    rendered = render_html(conversation, args.summary or "Session trace", "Claude Code",
                           args.max_output, not args.no_thinking, args.max_images, args.assistant,
                           not args.keep_paths)
    out_file.write_text(rendered, encoding="utf-8")
    print(f"wrote {out_file} ({len(rendered) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
