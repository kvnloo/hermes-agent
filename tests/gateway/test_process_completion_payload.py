"""Bot reply payloads survive the agent-notify completion path."""
import json
from types import SimpleNamespace

import pytest
from gateway.run_notifications import GatewayNotificationsMixin
from tools.process_registry_notifications import format_process_notification


def completion(raw, limit):
    session = SimpleNamespace(command="synthetic-reply", output_buffer=raw, exit_code=0,
                              completion_output_chars=limit, task_id="", started_at=1.0,
                              parent_session_id="parent")
    return GatewayNotificationsMixin._build_process_completion_event({}, session, "proc_test")


def test_bot_reply_preserves_full_multiline_json_payload():
    reply = "\n".join(f"Synthetic achievement {i}: " + "x" * 400 for i in range(8))
    raw = json.dumps({"reply": reply}) + "\n"
    evt = completion(raw, 18000)
    assert evt["output"] == raw
    assert raw in format_process_notification(evt)
    assert evt.get("output_cut", 0) == 0


@pytest.mark.parametrize("limit", [0, 18000])
def test_truncated_single_line_never_disappears_at_terminal_newline(limit):
    raw = "x" * 20000 + "\n"
    evt = completion(raw, limit)
    assert evt["output"].strip()
    assert evt["output"].endswith("x\n")
    assert evt["output_cut"] > 0

@pytest.mark.parametrize("limit", [0, 18000])
@pytest.mark.parametrize("redaction_enabled", [False, True], ids=["redaction-off", "redaction-on"])
def test_completion_redacts_prefix_cut_by_tail_window(monkeypatch, limit, redaction_enabled):
    """A completion must mask a token before clipping hides its recognizable prefix."""
    import agent.redact as redact

    monkeypatch.setattr(redact, "_REDACT_ENABLED", redaction_enabled)
    body = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklm"
    window = limit or 2000
    # Put the sk- prefix just outside the kept window, in both budget modes.
    raw = "x" * 150 + " sk-" + body + " " * (window - len(body) - 1) + "\n"
    assert raw[-window:].startswith(body)

    event = completion(raw, limit)
    assert body not in event["output"]
    assert body not in format_process_notification(event)
