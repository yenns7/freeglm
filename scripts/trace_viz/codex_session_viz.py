#!/usr/bin/env python3
"""Codex session rollout JSONL → a self-contained HTML cookbook trace.

The **Codex** visualizer — sibling of `claude_session_viz.py`. It parses Codex's `rollout-*.jsonl`
(under `~/.codex/sessions/<yyyy>/<mm>/<dd>/`) and hands a normalized conversation to the shared
renderer in `_trace_html.py`, so a Codex trace looks identical to a Claude Code one.

Codex specifics handled here:
  • The transcript is the ordered `response_item` stream; `event_msg` entries mirror it.
  • Real user prompts are taken from `event_msg` `user_message` events, so injected context
    (developer/system messages, the AGENTS.md block) is dropped.
  • Reasoning is `encrypted_content` — unreadable — so thinking blocks are omitted.
  • Tool calls are `custom_tool_call` / `function_call`; their outputs (matched by `call_id`) hold
    `input_text` and `input_image` items — the data-URL images are split into media_type + base64.

Usage:
    python3 scripts/trace_viz/codex_session_viz.py <rollout>.jsonl \\
        --summary "Locate the cakes" -o cookbooks/core/case-core-codex-vision.html
    codex_session_viz.py <rollout.jsonl> [-o OUT] [--summary TEXT] [--assistant NAME]
                         [--max-output N] [--max-images N]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _trace_html import render_html


def _msg_text(payload: dict) -> str:
    return "\n".join(c.get("text", "") for c in payload.get("content", [])
                     if isinstance(c, dict) and c.get("type") in ("input_text", "output_text", "text"))


def _parse_data_uri(url: str) -> tuple[str, str]:
    """`data:image/jpeg;base64,XXXX` → ('image/jpeg', 'XXXX'); ('', '') if not embeddable."""
    if url.startswith("data:") and ";base64," in url:
        header, data = url.split(";base64,", 1)
        return header[len("data:"):] or "image/png", data
    return "", ""


def _norm_output(output) -> dict:
    """Normalize a Codex tool output into the shared {content:[…], is_error} shape."""
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            output = [{"type": "input_text", "text": output}]
    items: list[dict] = []
    for it in output if isinstance(output, list) else []:
        if not isinstance(it, dict):
            items.append({"type": "text", "text": str(it)})
        elif it.get("type") in ("input_text", "output_text", "text"):
            items.append({"type": "text", "text": it.get("text", "")})
        elif it.get("type") in ("input_image", "output_image", "image"):
            media, data = _parse_data_uri(it.get("image_url") or it.get("url") or "")
            if data:
                items.append({"type": "image", "source": {"media_type": media, "data": data}})
    return {"content": items, "is_error": False}


def parse_session(jsonl_path: str) -> list[dict]:
    """Return an ordered list of turns from a Codex rollout."""
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

    # 1) The genuine user prompts, from user_message events (injected context never appears here).
    prompts: set[str] = set()
    for obj in lines:
        if obj.get("type") == "event_msg":
            pl = obj.get("payload", {})
            if pl.get("type") == "user_message":
                txt = (pl.get("message") or pl.get("text") or "").strip()
                if txt:
                    prompts.add(txt)

    # 2) Walk the response_item stream into turns.
    conversation: list[dict] = []
    results: dict[str, dict] = {}
    cur: dict | None = None

    def ensure_turn() -> dict:
        nonlocal cur
        if cur is None:
            cur = {"user_text": "", "blocks": []}
            conversation.append(cur)
        return cur

    for obj in lines:
        if obj.get("type") != "response_item":
            continue
        pl = obj.get("payload", {})
        pt = pl.get("type")
        if pt == "message":
            role = pl.get("role")
            if role == "user":
                text = _msg_text(pl).strip()
                if text in prompts:                 # a real prompt → new turn
                    cur = {"user_text": text, "blocks": []}
                    conversation.append(cur)
                # else: injected developer/AGENTS context → skip
            elif role == "assistant":
                text = _msg_text(pl).strip()
                if text:
                    ensure_turn()["blocks"].append({"kind": "text", "text": text})
            # role == "developer" → skip
        elif pt in ("custom_tool_call", "function_call"):
            ensure_turn()["blocks"].append({
                "kind": "tool",
                "name": pl.get("name", ""),
                "id": pl.get("call_id", ""),
                "input": pl.get("input") if pt == "custom_tool_call" else pl.get("arguments"),
            })
        elif pt in ("custom_tool_call_output", "function_call_output"):
            results[pl.get("call_id", "")] = _norm_output(pl.get("output"))
        # reasoning (encrypted) → skip

    for turn in conversation:
        turn["results"] = results
    return [t for t in conversation if t["user_text"] or t["blocks"]]


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a Codex session rollout JSONL as a self-contained HTML trace.")
    ap.add_argument("jsonl", help="path to the rollout .jsonl")
    ap.add_argument("-o", "--output", help="output HTML file (default: <rollout>.html in cwd)")
    ap.add_argument("--summary", help="page title (default: 'Session trace')")
    ap.add_argument("--assistant", default="Qwen3.8 Max",
                    help='label for the assistant role (default: "Qwen3.8 Max")')
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
        ap.error("no turns found — is this a Codex rollout .jsonl?")

    out_file = Path(args.output) if args.output else Path(Path(args.jsonl).with_suffix(".html").name)
    rendered = render_html(conversation, args.summary or "Session trace", "Codex",
                           args.max_output, True, args.max_images, args.assistant,
                           not args.keep_paths)
    out_file.write_text(rendered, encoding="utf-8")
    print(f"wrote {out_file} ({len(rendered) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
