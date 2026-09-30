from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "lab" / "z0_hermes_observer" / "shadow_api_failure.py"


def _load():
    spec = importlib.util.spec_from_file_location("shadow_api_failure_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _event(event, call, *, request_id="req", **fields):
    return {
        "schema": "z0int.hermes_observer_event.v1",
        "event": event,
        "identity": {
            "harness_id": "hermes",
            "session_id": "s",
            "task_id": "task",
            "turn_id": "t",
            "trace_id": "trace",
            "api_request_id": request_id,
        },
        "fields": {"api_call_count": call, **fields},
    }


def test_joins_objective_success_and_failure_labels():
    module = _load()
    rows = [
        _event("pre_api_request", 1, provider="p", model="m", approx_input_tokens=100),
        _event("post_api_request", 1),
        _event("pre_api_request", 2, request_id="req2", provider="p", model="m", retry_count=1),
        _event("api_request_error", 2, request_id="req2", status_code=429, retryable=True),
    ]
    examples = module.joined_examples(rows)
    assert [row["verified_outcome"] for row in examples] == [False, True]
    assert [row["outcome_source"] for row in examples] == ["post_api_request", "api_request_error"]
    assert examples[0]["request"]["state"]["approx_input_tokens"] == 100
    assert examples[1]["request"]["state"]["retry_count"] == 1


def test_unclosed_or_orphan_events_are_not_labeled():
    module = _load()
    rows = [
        _event("pre_api_request", 1),
        _event("post_api_request", 9, request_id="orphan"),
    ]
    assert module.joined_examples(rows) == []


def test_request_is_bounded_metadata_not_content():
    module = _load()
    pre = _event(
        "pre_api_request", 1, provider="p", model="m", message_count=5,
        request_char_count=999, platform="cli"
    )
    pre["request"] = {"body": {"messages": [{"content": "secret"}]}}
    request = module.request_for(pre)
    rendered = str(request)
    assert "secret" not in rendered
    assert request["questions"][0]["id"] == "api.attempt_will_fail"
    assert request["state"]["message_count"] == 5
