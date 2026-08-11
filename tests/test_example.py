"""Smoke test for the example/template capability — also shows how to test a capability.

conftest auto-discovers freeglm_example (it scans src/capabilities/*/ for the server
package), so it imports like any other server.
"""

import json

import freeglm_example as ex


def test_lists_the_demo_tools():
    names = {t["name"] for t in ex.list_tools()}
    assert names == {"echo", "make_swatch", "make_film_strip", "describe", "config_probe"}


def test_echo_returns_text():
    content = ex.get_handler("echo")({"message": "hi", "repeat": 2})
    assert content[0]["type"] == "text"
    assert content[0]["text"] == "hi\nhi"


def test_swatch_returns_an_image():
    content = ex.get_handler("make_swatch")({"size": 32})
    assert any(b["type"] == "image" and b["data"] for b in content)


def test_film_strip_returns_a_frame_per_image():
    content = ex.get_handler("make_film_strip")({"frames": 3, "size": 48})
    images = [b for b in content if b["type"] == "image"]
    assert len(images) == 3


def test_describe_dry_run_returns_request_without_calling_api():
    # dry_run needs no API key or network — it returns the request that WOULD be sent.
    content = ex.get_handler("describe")({"prompt": "hello", "dry_run": True})
    assert content[0]["type"] == "text"
    assert "DRY RUN" in content[0]["text"]
    preview = json.loads(content[0]["text"].split("\n", 1)[1])
    assert preview["messages"][0]["content"][-1] == {"type": "text", "text": "hello"}


def test_config_probe_reports_env_with_default(monkeypatch):
    monkeypatch.delenv("FREEGLM_EXAMPLE_GREETING", raising=False)
    content = ex.get_handler("config_probe")({})
    assert content[0]["type"] == "text"
    assert "hello from the example capability" in content[0]["text"]
