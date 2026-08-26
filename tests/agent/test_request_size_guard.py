import json
import sys
from types import SimpleNamespace

import pytest

from agent.request_size_guard import (
    RequestBodyTooLarge,
    guard_request_body_size,
)
from agent.transports.codex import ResponsesApiTransport


def _codex_payload(tool_output: str) -> dict:
    return {
        "model": "gpt-5.6-sol",
        "instructions": "system",
        "input": [
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "work"}]},
            {"type": "function_call", "call_id": "call_big", "name": "terminal", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "call_big", "output": tool_output},
        ],
        "stream": True,
    }


def test_codex_preflight_spills_large_tool_output_before_serialization(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    original = "HEAD\n" + ("middle-secret-shape\n" * 200_000) + "TAIL"
    payload = _codex_payload(original)

    guarded, report = guard_request_body_size(
        payload,
        max_body_bytes=200_000,
        max_inline_tool_chars=32_000,
    )

    assert report.reason == "oversized_tool_results"
    assert report.before_bytes > 3_000_000
    assert report.after_bytes < 200_000
    assert report.compacted_tool_results == 1
    replacement = guarded["input"][2]["output"]
    assert "HEAD" in replacement
    assert "TAIL" in replacement
    assert "Full output saved to:" in replacement
    saved_path = replacement.split("Full output saved to: ", 1)[1].splitlines()[0]
    assert open(saved_path, encoding="utf-8").read() == original


def test_chat_completions_tool_output_uses_same_provider_neutral_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    original = "start\n" + ("x" * 500_000) + "\nend"
    payload = {
        "model": "provider/model",
        "messages": [
            {"role": "assistant", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "terminal", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": original},
        ],
    }

    guarded, report = guard_request_body_size(
        payload,
        max_body_bytes=100_000,
        max_inline_tool_chars=20_000,
    )

    assert report.after_bytes < report.before_bytes
    assert "start" in guarded["messages"][1]["content"]
    assert "end" in guarded["messages"][1]["content"]
    assert guarded["messages"][1]["content"] != original


def test_small_request_is_byte_stable_and_not_copied():
    payload = _codex_payload("small actionable result")
    before = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()

    guarded, report = guard_request_body_size(payload, max_body_bytes=100_000)

    assert guarded is payload
    assert json.dumps(guarded, ensure_ascii=False, separators=(",", ":")).encode() == before
    assert report.before_bytes == report.after_bytes
    assert report.reason == "within_budget"


def test_preflight_fails_closed_before_transport_when_non_tool_body_remains_oversized():
    payload = _codex_payload("small")
    payload["instructions"] = "system" * 100_000

    with pytest.raises(RequestBodyTooLarge) as exc:
        guard_request_body_size(payload, max_body_bytes=50_000)

    message = str(exc.value)
    assert "request body remains oversized" in message.lower()
    assert "before_bytes=" in message
    assert "after_bytes=" in message
    assert "systemsystem" not in message


def test_repeated_preflight_is_idempotent_and_does_not_duplicate_spill_footer(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    payload = _codex_payload("head\n" + ("z" * 500_000) + "\ntail")

    first, _ = guard_request_body_size(payload, max_body_bytes=100_000, max_inline_tool_chars=20_000)
    second, report = guard_request_body_size(first, max_body_bytes=100_000, max_inline_tool_chars=20_000)

    assert second is first
    assert report.compacted_tool_results == 0
    assert second["input"][2]["output"].count("Full output saved to:") == 1


def test_exact_codex_transport_serialization_is_bounded_with_repeated_notifications(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setitem(
        sys.modules,
        "run_agent",
        SimpleNamespace(DEFAULT_AGENT_IDENTITY="default system"),
    )
    giant = "HEAD\n" + ("tool-data\n" * 300_000) + "TAIL"
    messages = [
        {"role": "system", "content": "stable system"},
        {"role": "user", "content": "work"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "call_big",
                "type": "function",
                "function": {"name": "terminal", "arguments": "{}"},
            }],
        },
        {"role": "tool", "tool_call_id": "call_big", "name": "terminal", "content": giant},
    ]
    for i in range(12):
        messages.extend([
            {"role": "assistant", "content": f"notification {i}"},
            {"role": "user", "content": f"queued interrupt {i}"},
        ])

    payload = ResponsesApiTransport().build_kwargs(
        "gpt-5.6-sol",
        messages,
        provider="openai-codex",
        is_codex_backend=True,
    )
    raw_bytes = len(json.dumps(payload, ensure_ascii=False).encode())
    guarded, report = guard_request_body_size(
        payload,
        max_body_bytes=200_000,
        max_inline_tool_chars=30_000,
    )

    assert raw_bytes > 2_000_000
    assert report.after_bytes < 200_000
    outputs = [item["output"] for item in guarded["input"] if item.get("type") == "function_call_output"]
    assert len(outputs) == 1
    assert "HEAD" in outputs[0] and "TAIL" in outputs[0]


def test_small_tool_image_attachment_is_preserved_byte_for_byte():
    payload = {
        "model": "vision-model",
        "messages": [{
            "role": "tool",
            "tool_call_id": "vision-1",
            "content": [
                {"type": "text", "text": "inspection"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
            ],
        }],
    }
    before = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    guarded, report = guard_request_body_size(payload, max_body_bytes=100_000)

    assert guarded is payload
    assert json.dumps(guarded, ensure_ascii=False, separators=(",", ":")) == before
    assert report.reason == "within_budget"
