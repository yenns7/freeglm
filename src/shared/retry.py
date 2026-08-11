"""One retry/backoff policy for the network clients.

api_openai (chat), api_dashscope (async services) and core's serper client all need the
same attempt/backoff loop; before this they hand-rolled four slightly different copies.
This centralizes the *mechanism* while leaving each caller's policy (attempt count, backoff
shape, which errors are retryable, and whether to raise or return None on exhaustion) as
call-site arguments — different endpoints legitimately warrant different policies.
"""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Callable, TypeVar

_log = logging.getLogger(__name__)
T = TypeVar("T")


_URL_SECRET_RE = re.compile(r"(https?://[^\s?#]+)(?:[?#][^\s]*)", re.IGNORECASE)
_NAMED_SECRET_RE = re.compile(
    r"""(?ix)
    \b(
        authorization|proxy-authorization|bearer|
        api[-_ ]?key|token|access[-_ ]?(?:key(?:[-_ ]?id)?|token)|auth[-_ ]?token|
        client[-_ ]?secret|secret(?:[-_ ]?key)?|signature|password|
        [a-z][a-z0-9_]*(?:_api_key|_token|_secret|_secret_key|_password)|
        oss_(?:ak|sk)
    )\b[\"']?\s*[:=]\s*(?:bearer\s+)?[\"']?[^\s,;)\]}]+[\"']?
    """
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{4,}")
_COMMON_TOKEN_RE = re.compile(
    r"\b(?:sk-[a-z0-9_-]{8,}|eyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,})\b",
    re.IGNORECASE,
)


def redact_sensitive_error(error: Exception | str) -> str:
    """Return a bounded diagnostic with signed URLs and credential-like values redacted."""
    message = str(error)
    message = _URL_SECRET_RE.sub(r"\1?<redacted>", message)
    message = _NAMED_SECRET_RE.sub(r"\1=<redacted>", message)
    message = _BEARER_RE.sub("Bearer <redacted>", message)
    message = _COMMON_TOKEN_RE.sub("<redacted>", message)
    return message[:200]


def _wait_seconds(attempt: int, base: float, mode: str, cap: float | None, jitter: float = 0.0) -> float:
    wait = base * attempt if mode == "linear" else base * (2 ** (attempt - 1))
    if jitter:
        wait += random.uniform(0.0, jitter)
    if cap is not None:  # cap bounds the final sleep, jitter included
        wait = min(wait, cap)
    return wait


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int,
    base_backoff: float = 1.0,
    mode: str = "linear",  # "linear" → base*attempt; "exp" → base*2**(attempt-1)
    cap: float | None = None,  # ceiling (seconds) on the inter-attempt sleep
    jitter: float = 0.0,  # add uniform(0, jitter) seconds on top of each sleep (de-syncs retry herds)
    should_retry: Callable[[Exception], bool] | None = None,
    on_exhausted: str = "raise",  # "raise" the last error, or "none" → return None
    log: logging.Logger = _log,
) -> T | None:
    """Call ``fn()`` with retry.

    Retries while ``should_retry(exc)`` (default: any exception); an exception the predicate
    rejects propagates immediately. After ``attempts`` tries either re-raises the last
    exception (``on_exhausted="raise"``) or returns ``None`` (``on_exhausted="none"``).
    """
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — the predicate decides what is retryable
            if should_retry is not None and not should_retry(e):
                raise
            last = e
            if attempt == attempts:
                break
            wait = _wait_seconds(attempt, base_backoff, mode, cap, jitter)
            # API errors can embed signed URLs, headers, or payload fragments. Sanitize before the
            # message reaches stderr, which many harnesses persist as an MCP log.
            log.warning(
                "call failed (attempt %d/%d): %s: %s — retrying in %.1fs",
                attempt,
                attempts,
                type(e).__name__,
                redact_sensitive_error(e),
                wait,
            )
            time.sleep(wait)
    if on_exhausted == "raise":
        if last is None:  # attempts < 1 → the loop never ran; explicit (assert vanishes under -O)
            raise RuntimeError(f"retry_call made no attempt (attempts={attempts})")
        raise last
    return None
