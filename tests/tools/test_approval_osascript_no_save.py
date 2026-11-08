"""Regression for NousResearch/hermes-agent#141346 (unsaved PowerPoint data loss).

No AppleScript is executed; only the terminal approval gate is exercised.
"""
import pytest

from tools import approval, approval_context
from tools.approval_detection import detect_dangerous_command


_DECK_CLOSE = (
    'osascript -e \'tell application "Microsoft PowerPoint"\n'
    'open POSIX file "/tmp/traz.pptx"\n'
    'save active presentation in POSIX file "/tmp/traz.pdf" as save as PDF\n'
    'close active presentation saving no\n'
    "end tell'"
)


def test_smart_guardian_cannot_approve_unsaved_deck_close(monkeypatch):
    """Even a guardian APPROVE must not replace the operator's decision."""
    monkeypatch.setenv("HERMES_INTERACTIVE", "1")
    monkeypatch.delenv("HERMES_CRON_SESSION", raising=False)
    monkeypatch.delenv("HERMES_GATEWAY_SESSION", raising=False)
    monkeypatch.setattr(approval, "_YOLO_MODE_FROZEN", False)
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "smart")
    monkeypatch.setattr(approval, "_command_matches_permanent_allowlist", lambda _: False)
    monkeypatch.setattr(approval, "get_current_session_key", lambda: "test-141346-unsaved-deck")
    monkeypatch.setattr(approval, "_approval_scope", lambda *_: None)

    def guardian_must_not_decide(*_args, **_kwargs):
        pytest.fail("smart guardian is not an operator approval")

    monkeypatch.setattr(approval, "_smart_verdict", guardian_must_not_decide)
    asked = []
    result = approval.check_all_command_guards(
        _DECK_CLOSE, "local", approval_callback=lambda *_a, **_k: asked.append(True) or "deny",
    )
    assert result["approved"] is False
    assert asked == [True]
    assert detect_dangerous_command(_DECK_CLOSE)[1] == (
        "AppleScript closes or quits a document without saving"
    )


@pytest.mark.parametrize("executable", ["osascript", "/usr/bin/osascript", "command osascript"])
def test_command_position_osascript_close_is_flagged(executable):
    command = f"{executable} -e 'tell application \"Keynote\" to close front document saving no'"
    assert detect_dangerous_command(command)[0] is True


@pytest.mark.parametrize("command", [
    'osascript -e \'tell application "Keynote" to get name of front document\'',
    'echo \'osascript -e "close front document saving no"\'',
])
def test_safe_osascript_or_quoted_prose_does_not_trigger(command):
    assert detect_dangerous_command(command) == (False, None, None)
