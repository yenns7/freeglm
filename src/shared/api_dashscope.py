"""DashScope native-REST helpers for the async generation services (image / tts / video).

Submit a long-running task, poll it to SUCCEEDED/FAILED, download the artifact. Used by the
video-edit capability's generation tools. The OpenAI-compatible chat path (vision_chat / ocr /
grounding) lives in `api_openai`. `requests` is imported lazily so tool discovery stays cheap.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, TypeVar

from shared.env import get_env

log = logging.getLogger(__name__)


def _native_base_url() -> str:
    """DashScope native (non-OpenAI) REST base.

    Derived from the host of DASHSCOPE_BASE_URL when set, so pointing at the international endpoint
    (dashscope-intl.aliyuncs.com) or a proxy also redirects the generation services. Falls back to
    the public default when unset or malformed (incl. a non-http(s) scheme) — identical behavior to
    before for users who don't set it.
    """
    base = (get_env("DASHSCOPE_BASE_URL") or "").strip()
    if base:
        from urllib.parse import urlsplit

        p = urlsplit(base)
        if p.scheme in ("http", "https") and p.netloc:
            return f"{p.scheme}://{p.netloc}/api/v1"
    return "https://dashscope.aliyuncs.com/api/v1"


API_V1 = _native_base_url()  # DashScope native (non-OpenAI) REST base

# Generic transient-retry wrapper for the generation services (image / tts / video),
# which poll long-running DashScope jobs and tolerate more retries than a chat call.
_SERVICE_MAX_RETRIES = 10
_SERVICE_RETRY_BACKOFF = 1.0

# DashScope rate limits (Throttling.RateQuota and friends) get their own exponential backoff
# on top of the linear transient preset: quota pressure clears on a longer time scale than a
# network blip, and hammering it linearly just extends the limit.
_THROTTLE_MAX_RETRIES = 4
_THROTTLE_BASE_BACKOFF = 2.0
_THROTTLE_JITTER = 1.0

T = TypeVar("T")


class ThrottlingError(RuntimeError):
    """A DashScope Throttling.* rate-limit outcome, normalized from either error path."""


def _throttle_code(result: Any) -> str | None:
    """Throttling.* code carried in a result body (SDK response `.code` / raw REST dict), if any."""
    code = result.get("code") if isinstance(result, dict) else getattr(result, "code", None)
    return code if isinstance(code, str) and code.startswith("Throttling") else None


def _call_normalized(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Call *fn*, surfacing a DashScope Throttling.* rate limit as ThrottlingError.

    Covers both paths a limit arrives on: an HTTP-layer exception (raise_for_status on a 429)
    whose JSON body carries the code, and an HTTP 200/4xx SDK/REST result whose body carries it
    (the dashscope SDK never raises — it returns a response object with `.code`).
    """
    try:
        result = fn(*args, **kwargs)
    except Exception as e:
        resp = getattr(e, "response", None)
        if resp is not None:
            try:
                code = resp.json().get("code")
            except Exception:
                code = None
            if isinstance(code, str) and code.startswith("Throttling"):
                raise ThrottlingError(f"[{code}] rate limited") from e
        raise
    code = _throttle_code(result)
    if code is not None:
        message = result.get("message", "") if isinstance(result, dict) else getattr(result, "message", "")
        raise ThrottlingError(f"[{code}] {message}")
    return result


def retry_call(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Call *fn* with linear-backoff retry on transient exceptions (up to _SERVICE_MAX_RETRIES),
    plus exponential backoff with jitter on DashScope Throttling.* rate limits (up to
    _THROTTLE_MAX_RETRIES).

    Applies the service preset (more retries than a chat call, since generation tools poll long
    jobs) over the shared retry policy. Throttled outcomes are normalized to ThrottlingError by
    _call_normalized and handled by the outer exponential loop, so every generation tool built on
    this module benefits without per-tool changes."""
    from shared.retry import retry_call as _retry

    def _service() -> T:
        return _retry(
            lambda: _call_normalized(fn, *args, **kwargs),
            attempts=_SERVICE_MAX_RETRIES,
            base_backoff=_SERVICE_RETRY_BACKOFF,
            mode="linear",
            should_retry=_service_retryable,
            on_exhausted="raise",
            log=log,
        )

    return _retry(
        _service,
        attempts=_THROTTLE_MAX_RETRIES,
        base_backoff=_THROTTLE_BASE_BACKOFF,
        mode="exp",
        jitter=_THROTTLE_JITTER,
        should_retry=lambda e: isinstance(e, ThrottlingError),
        on_exhausted="raise",
        log=log,
    )


def _service_retryable(error: Exception) -> bool:
    """Retry transient failures, but fail fast on known permanent request/auth errors."""
    if isinstance(error, ThrottlingError):
        return False
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status in (408, 429) or status >= 500
    return True


def submit_dashscope_async(path: str, payload: dict, api_key: str, *, timeout: int = 30) -> tuple[str | None, dict]:
    """POST an async task to DashScope native REST (API_V1/<path>); return (task_id, raw_result)."""
    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    def _post() -> dict:
        r = requests.post(f"{API_V1}/{path}", headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()  # requests doesn't raise on 4xx/5xx by default — force it so retry_call retries
        return r.json()  # parsed inside the retry, so a throttled 200 body is seen by retry_call too

    result = retry_call(_post)
    return result.get("output", {}).get("task_id"), result


def save_url_to_dir(url: str, dest_path: str, timeout: int = 60) -> str:
    """Download `url` to `dest_path` (creating parent dirs), skipping the fetch if the file already
    exists. Retries transient download failures. Returns `dest_path`."""
    import requests

    os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
    if not os.path.exists(dest_path):

        def _get() -> bytes:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()  # don't write an error page's bytes to disk as the "artifact"
            return r.content

        content = retry_call(_get)
        with open(dest_path, "wb") as f:
            f.write(content)
    return dest_path


def poll_dashscope_task(task_id: str, api_key: str, *, base_url: str, interval: float, timeout: float) -> dict:
    """Poll a DashScope async task until it reaches SUCCEEDED/FAILED.

    Returns the raw response dict on SUCCEEDED/FAILED, or a synthetic TIMEOUT dict
    after `timeout` seconds. Callers format the terminal result themselves. Each poll's
    GET+json is retried together (a transient blip or truncated body must not abort an
    in-flight, already-billed job).
    """
    import requests

    headers = {"Authorization": f"Bearer {api_key}"}
    deadline = time.monotonic() + max(timeout, 0)

    def _poll() -> dict:
        r = requests.get(f"{base_url}/tasks/{task_id}", headers=headers, timeout=30)
        r.raise_for_status()  # retry transient 5xx on an already-billed job instead of aborting
        return r.json()

    while time.monotonic() < deadline:
        resp = retry_call(_poll)
        if resp.get("output", {}).get("task_status") in ("SUCCEEDED", "FAILED"):
            return resp
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(max(interval, 0), remaining))
    return {"output": {"task_status": "TIMEOUT", "task_id": task_id}}
