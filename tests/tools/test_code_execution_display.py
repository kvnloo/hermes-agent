"""Regression for #574: real kernels/RPC, literal stdout and optional eval companions."""
import json
from unittest.mock import patch

import pytest

from tests.tools._child_env_fixtures import child_env  # noqa: F401
from tools.code_execution_display import eval_progress_scope, present_execution
from tools.code_execution_tool import execute_code  # noqa: F401 -- registers the real tool
from tools.registry import registry


def run(code, reset=True):
    with patch("tools.code_execution_tool._load_config", return_value={"mode": "project", "timeout": 10}):
        result = registry.dispatch("execute_code", {"code": code, "reset": reset}, task_id="eval-test")
        return json.loads(result) if isinstance(result, str) else result


def test_real_kernel_print_views_preserve_stdout_and_do_not_leak_between_cells(child_env):
    snapshots = []
    with eval_progress_scope("call-a", lambda *args, **kw: snapshots.append(kw["eval_update"])):
        result = run('''from hermes_tools import print_view
print("😀 before")
print_view({"a": 1})
print("between")
print_view("# heading", kind="markdown")
print_view([["1", "2"]], kind="table", columns=["a", "b"])
print("after")
''')
    assert result["status"] == "success", result
    assert result["output"] == '😀 before\n{\n  "a": 1\n}\nbetween\n# heading\na | b\n1 | 2\nafter\n'
    cell = result["eval_display"]["cells"][0]
    assert [view["kind"] for view in cell["views"]] == ["json", "markdown", "table"]
    for view in cell["views"]:
        assert result["output"][view["start"]:view["start"] + len(view["printed"])] == view["printed"]
    assert snapshots[0]["cell"]["id"] == snapshots[-1]["cell"]["id"] == cell["id"]
    assert snapshots[0]["cell"]["status"] == "running"
    assert snapshots[-1]["cell"]["status"] == "done"
    assert all(s["tool_id"] == "call-a" for s in snapshots)
    assert snapshots[0]["cell"]["views"] == []  # immutable event snapshot
    second = run('print("next")', reset=False)
    assert second["kernel"]["reused"] is True
    assert second["eval_display"]["cells"][0]["id"] != cell["id"]
    assert second["eval_display"]["cells"][0]["views"] == []


def test_nested_real_read_reports_running_then_done_with_same_event_id(child_env):
    witness = child_env / "witness.txt"
    witness.write_text("real nested output\n")
    snapshots = []
    with eval_progress_scope("nested-call", lambda *args, **kw: snapshots.append(kw["eval_update"])):
        result = run(f'from hermes_tools import read_file\nprint(read_file({str(witness)!r})["content"])')
    assert "real nested output" in result["output"], result
    observed = [s["cell"]["events"] for s in snapshots if s["cell"]["events"]]
    assert observed[0][0]["status"] == "running"
    assert observed[-1][0]["status"] == "done"
    assert len({events[0]["id"] for events in observed}) == 1
    assert result["eval_display"]["cells"][0]["events"] == observed[-1]


def test_error_keeps_stdout_and_companion_status(child_env):
    result = run('print("before error")\nraise ValueError("actual failure")')
    assert result["status"] == "error"
    assert result["output"].startswith("before error\n")
    cell = result["eval_display"]["cells"][0]
    assert cell["status"] == "error"
    assert "actual failure" in cell["error"]


@pytest.mark.parametrize("status,expected", [("timeout", "timeout"), ("interrupted", "cancelled"), ("yielded_to_background", "background")])
def test_explicit_outcomes_do_not_become_success(status, expected):
    raw = json.dumps({"status": status, "output": "literal", "error": "problem"})
    result = json.loads(present_execution(lambda code: raw, "print(1)"))
    assert result["output"] == "literal"
    assert result["eval_display"]["cells"][0]["status"] == expected


def test_companions_cannot_bypass_redaction_or_recover_clipped_stdout(monkeypatch):
    from agent import redact
    monkeypatch.setattr(redact, "redact_sensitive_text", lambda text, **kw: text.replace("secret", "[redacted]"))
    raw = json.dumps({"status": "success", "output": "retained\n", "_printed_views": [
        {"id": "gone", "kind": "markdown", "start": 0, "printed": "secret\n"}
    ]})
    result = json.loads(present_execution(lambda code: raw, "secret"))
    assert result["output"] == "retained\n"
    assert result["eval_display"]["cells"][0]["views"] == []
    assert "secret" not in json.dumps(result)
