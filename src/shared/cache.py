"""Cache directory + content-keyed cache paths for derived render artifacts (compiled PDFs, etc.).

Part of the `shared` library (src/shared/) — stdlib-only. Lets heavy renderers skip recompilation
when their inputs are unchanged.
"""

from __future__ import annotations

import hashlib
import os
import sys

from shared.env import get_env


def cache_dir() -> str:
    """Directory for derived render artifacts, overridable via FREEGLM_CACHE.

    - macOS:   ~/Library/Caches/freeglm
    - Linux:   $XDG_CACHE_HOME/freeglm  (or ~/.cache/freeglm)
    - Windows: %LOCALAPPDATA%\\freeglm\\cache
    """
    override = get_env("FREEGLM_CACHE")
    if override:
        base = override
    elif sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
        base = os.path.join(local, "freeglm", "cache")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Caches/freeglm")
    else:
        xdg = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
        base = os.path.join(xdg, "freeglm")
    os.makedirs(base, exist_ok=True)
    return base


def cached_path(src: str, suffix: str, extra_files: list[str] | None = None) -> str:
    """Stable cache path for an artifact derived from `src`.

    Keyed by path + mtime + size of `src` and of every file in `extra_files`, so editing any input
    yields a new path (cache miss) while unchanged inputs reuse the artifact.
    """

    def _stamp(p: str) -> str:
        try:
            st = os.stat(p)
            return f"{os.path.abspath(p)}:{st.st_mtime_ns}:{st.st_size}"
        except OSError:
            return os.path.abspath(p)

    inputs = [src, *sorted(extra_files or [])]
    key = "|".join(_stamp(p) for p in inputs)
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    base = os.path.splitext(os.path.basename(src))[0]
    return os.path.join(cache_dir(), f"{base}-{digest}.{suffix}")
