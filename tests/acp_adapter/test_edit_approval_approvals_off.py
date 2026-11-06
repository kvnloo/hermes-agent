"""The ACP edit gate must honour the operator's "do not ask me" switches.

Every other Hermes approval gate (dangerous commands, plugin rules, SSH-config writes,
execute_code) resolves from ``approvals.mode: off`` / ``/yolo`` instead of parking a prompt. The
edit gate did not, so a session whose approvals were off still waited ``approvals.timeout``
per edit and then heard the edit had been "denied" — kvnloo/oss-factory#320: 90 blocked
edits/week across 52 T3 Code sessions, 5.5 agent-hours stalled, 17 Mtok of context re-sent, and
38 of the blocks were followed by the agent editing the same file through terminal.
"""

from __future__ import annotations

import json

from acp_adapter.edit_approval import set_edit_approval_requester
from model_tools import handle_function_call


def teardown_function() -> None:
    set_edit_approval_requester(None)


def _write(target, content="switched off\n"):
    """A write through the real tool dispatcher, with the edit gate bound to a hard Deny."""
    set_edit_approval_requester(lambda _proposal: False)
    return json.loads(handle_function_call(
        "write_file", {"path": str(target), "content": content}, task_id="acp-edit-approvals-off"))


def test_approvals_off_lets_the_edit_run_instead_of_timing_out(tmp_path, monkeypatch):
    """``approvals.mode: off`` (the Desktop toggle writes it) must reach the edit gate too."""
    from tools import approval_context
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "off")
    target = tmp_path / "unattended.txt"  # net-new: no stale-write guard to mask the verdict

    result = _write(target)

    assert "error" not in result, result
    assert target.read_text(encoding="utf-8") == "switched off\n"


def test_session_yolo_lets_the_edit_run(tmp_path, monkeypatch):
    from tools import approval
    monkeypatch.setattr(approval, "is_session_yolo_enabled", lambda _key: True)
    monkeypatch.setattr(approval, "_YOLO_MODE_FROZEN", False)
    target = tmp_path / "yolo.txt"

    result = _write(target)

    assert "error" not in result, result
    assert target.read_text(encoding="utf-8") == "switched off\n"


def test_manual_mode_still_prompts_and_a_deny_blocks(tmp_path, monkeypatch):
    """The bypass is the operator's switch, not a hole: manual/smart sessions keep the prompt."""
    from tools import approval_context
    monkeypatch.setattr(approval_context, "_get_approval_mode", lambda: "manual")
    target = tmp_path / "asked.txt"
    target.write_text("before\n", encoding="utf-8")

    result = _write(target, "after\n")

    assert "error" in result
    assert "Edit approval denied by ACP client" in result["error"]
    assert target.read_text(encoding="utf-8") == "before\n"


def test_an_unbuildable_diff_is_not_reported_as_a_denial(tmp_path):
    """The diff that never reached a client is not a refusal: the agent's patch did not match."""
    target = tmp_path / "stale.txt"
    target.write_text("alpha\n", encoding="utf-8")
    set_edit_approval_requester(lambda _proposal: True)

    result = json.loads(handle_function_call(
        "patch", {"mode": "replace", "path": str(target),
                  "old_string": "no such line\n", "new_string": "x\n"},
        task_id="acp-edit-no-diff"))

    assert "denied" not in result["error"]
    assert "could not be prepared" in result["error"]
    assert "Re-read the file" in result["error"]
    assert target.read_text(encoding="utf-8") == "alpha\n"
