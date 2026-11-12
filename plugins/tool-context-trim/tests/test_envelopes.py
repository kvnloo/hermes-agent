"""HZ21 envelope regressions. Generated public text, never chat history."""

import importlib.util
import json
import os
from pathlib import Path

import pytest

PLUGIN = Path(os.environ.get("HZ21_TEST_PLUGIN_SOURCE", str(Path(__file__).resolve().parents[1]))) / "__init__.py"
ARGS = {"path": "/public/example.py"}
TEXT = ('line of public code: "hello" \\ example\n' * 2000)[:60_000]
MARKER = "[z21 tool-output trim"


@pytest.fixture
def mod(monkeypatch):
    for name in ("MAX_CHARS", "HEAD", "TAIL", "DEDUPE_HEAD", "OFF", "OWNER_PATHS"):
        monkeypatch.delenv("Z21_TRIM_" + name, raising=False)
    spec = importlib.util.spec_from_file_location("z21_envelopes", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_session_cwd", lambda task_id: "")
    return module


def call(mod, result, args=None):
    return mod._on_transform_tool_result(
        tool_name="read_file", args=ARGS if args is None else args,
        result=result, session_id="hz21")


@pytest.mark.parametrize("key", ["content", "text", "output", "stdout"])
@pytest.mark.parametrize("size", [32_255, 60_000])
def test_single_text_envelope_is_capped(mod, key, size):
    original = TEXT[:size]
    payload = json.dumps({key: original})
    out = call(mod, payload)
    assert out is not None
    parsed = json.loads(out)
    assert set(parsed) == {key}
    inner = parsed[key]
    assert inner.find(MARKER) == 2402
    assert inner[:2400] == original[:2400]
    assert inner[-800:] == original[-800:]
    assert len(out) < 4200
    print(f"{key}: input={len(payload)} output={len(out)} marker={inner.find(MARKER)}")


@pytest.mark.parametrize("payload", [
    {"success": True, "diff": TEXT},
    {"content": TEXT, "total_lines": 2000},
    {"_multimodal": True, "content": [{"type": "text", "text": TEXT}]},
    {"content": [TEXT]}, {"content": 42}, {"other": TEXT}, [TEXT],
    {"content": json.dumps({"rows": [TEXT]})},
])
def test_structured_payload_stays_exact_on_repeated_reads(mod, payload):
    result = json.dumps(payload)
    assert call(mod, result) is None
    assert call(mod, result) is None


@pytest.mark.parametrize("private", [
    "/mnt/zer0models/sft-svlm/example.txt", "/home/kvn/.hermes/profiles/clean/example.txt",
    "auth", "secret", "token", "credential", "password", ".env",
])
def test_private_inner_text_is_exempt_even_after_cached_public_read(mod, private):
    call(mod, json.dumps({"content": TEXT}))
    result = json.dumps({"content": TEXT[:5000] + private + TEXT[5000:]})
    assert call(mod, result) is None
    assert call(mod, result) is None


@pytest.mark.parametrize("args", [
    {"path": "/mnt/zer0models/sft-svlm/example.txt"}, {"path": "/public/auth.py"},
])
def test_private_args_stay_exact_on_repeated_reads(mod, args):
    result = json.dumps({"content": TEXT})
    assert call(mod, result, args) is None
    assert call(mod, result, args) is None


def test_owner_path_override_checks_inner_text(mod, monkeypatch):
    monkeypatch.setenv("Z21_TRIM_OWNER_PATHS", "/private/project:/other/data")
    result = json.dumps({"content": TEXT + "see /private/project/file.py"})
    assert call(mod, result) is None
    assert call(mod, result) is None


def test_plain_text_still_trims(mod):
    out = call(mod, TEXT)
    assert out is not None
    assert out.find(MARKER) == 2402


@pytest.mark.parametrize("key", ["content", "text", "output", "stdout"])
def test_envelope_dedupe_remains_json(mod, key):
    result = json.dumps({key: TEXT})
    call(mod, result)
    out = call(mod, result)
    assert out is not None
    parsed = json.loads(out)
    assert set(parsed) == {key}
    assert parsed[key][:1600] == TEXT[:1600]
    assert parsed[key].find("[z21 dedupe") == 1602


def test_envelope_respects_existing_knobs(mod, monkeypatch):
    for key, value in {"MAX_CHARS": "1000", "HEAD": "400", "TAIL": "200", "DEDUPE_HEAD": "300"}.items():
        monkeypatch.setenv("Z21_TRIM_" + key, value)
    result = json.dumps({"content": TEXT})
    out = call(mod, result)
    assert out is not None
    assert json.loads(out)["content"].find(MARKER) == 402
    assert json.loads(out)["content"].endswith(TEXT[-200:])
    duplicate = call(mod, result)
    assert json.loads(duplicate)["content"].find("[z21 dedupe") == 302


def test_kill_switch_preserves_envelope(mod, monkeypatch):
    monkeypatch.setenv("Z21_TRIM_OFF", "1")
    result = json.dumps({"content": TEXT})
    assert call(mod, result) is None
    assert call(mod, result) is None


def test_short_inner_text_is_not_measured_as_escaped_json(mod):
    result = json.dumps({"content": "\n" * 3000})
    assert len(result) > 4000
    assert call(mod, result) is None


def test_write_invalidates_envelope_cache(mod):
    result = json.dumps({"content": TEXT})
    call(mod, result)
    mod._on_transform_tool_result(tool_name="write_file", result="ok", session_id="hz21")
    out = call(mod, result)
    assert json.loads(out)["content"].find(MARKER) == 2402
    assert "[z21 dedupe" not in out


def test_private_cwd_stays_exact_on_repeated_reads(mod, monkeypatch):
    monkeypatch.setattr(mod, "_session_cwd", lambda task_id: "/mnt/zer0models/sft-svlm")
    result = json.dumps({"content": TEXT})
    assert call(mod, result) is None
    assert call(mod, result) is None
