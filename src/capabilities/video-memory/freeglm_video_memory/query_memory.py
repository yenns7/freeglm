#!/usr/bin/env python3
"""CLI to query graph memory.

Usage:
    python query_memory.py <memory_dir> <command> [args...]

Commands:
    summary                          Video summary + super event list
    macros [super_id]                List macro events
    subgraph <macro_id>              Full subgraph detail
    search <query> [top_k]           Semantic search
    ocr <query> [top_k]              Search on-screen text
    time <start_sec> <end_sec>       Find macros by time range
"""

from __future__ import annotations

import os
import sys

# Run-from-source: make this package importable.
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if "freeglm_video_memory" not in sys.modules:
    sys.path.insert(0, os.path.dirname(_PKG_DIR))

from freeglm_video_memory.loader import load_toolkit  # noqa: E402


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    memory_dir = sys.argv[1]
    command = sys.argv[2]
    args = sys.argv[3:]

    try:
        toolkit = load_toolkit(memory_dir)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if command == "summary":
        print(toolkit.get_summary())
        print("\n--- Super Events ---")
        print(toolkit.get_super_events())

    elif command == "macros":
        super_id = args[0] if args else ""
        print(toolkit.get_macro_events(super_id=super_id))

    elif command == "subgraph":
        if not args:
            print("ERROR: subgraph requires macro_id", file=sys.stderr)
            sys.exit(1)
        print(toolkit.get_subgraph(args[0]))

    elif command == "search":
        if not args:
            print("ERROR: search requires query", file=sys.stderr)
            sys.exit(1)
        query = args[0]
        top_k = int(args[1]) if len(args) > 1 else 10
        print(toolkit.search_nodes(query=query, top_k=top_k))

    elif command == "ocr":
        if not args:
            print("ERROR: ocr requires query", file=sys.stderr)
            sys.exit(1)
        query = args[0]
        top_k = int(args[1]) if len(args) > 1 else 10
        print(toolkit.search_ocr_text(query=query, top_k=top_k))

    elif command == "time":
        start = float(args[0]) if args else 0
        end = float(args[1]) if len(args) > 1 else start + 600
        print(toolkit.search_by_time(start_sec=start, end_sec=end))

    else:
        print(f"ERROR: unknown command '{command}'", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
