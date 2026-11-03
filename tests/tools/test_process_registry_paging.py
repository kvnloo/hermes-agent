"""Regression for #141988, reported by kagankongar; prior patch by 686f6c61."""

import json
import time

from tools import process_registry as pr
from tools.process_registry import ProcessRegistry, ProcessSession


def _session():
    return ProcessSession(
        id="proc_page_test",
        command="echo lines",
        task_id="session-a",
        started_at=time.time(),
        output_buffer="line 0\nline 1\nline 2\nline 3\nline 4",
    )


def test_process_manage_log_numeric_strings_select_requested_window(monkeypatch):
    registry = ProcessRegistry()
    session = _session()
    registry._running[session.id] = session
    monkeypatch.setattr(pr, "process_registry", registry)

    result = json.loads(pr._handle_process({
        "action": "log", "session_id": session.id, "offset": "1", "limit": "2",
    }))
    assert result["output"].splitlines() == ["line 1", "line 2"]
    assert result["total_lines"] == 5

    # A missing offset still reads the tail, while an explicit zero starts at the head.
    assert registry.read_log(session.id, limit="2")["output"] == "line 3\nline 4"
    assert registry.read_log(session.id, offset="0", limit="2")["output"] == "line 0\nline 1"


def test_process_manage_invalid_paging_bound_is_a_tool_error(monkeypatch):
    registry = ProcessRegistry()
    session = _session()
    registry._running[session.id] = session
    monkeypatch.setattr(pr, "process_registry", registry)

    for field in ("offset", "limit"):
        result = json.loads(pr._handle_process({
            "action": "log", "session_id": session.id, field: "all",
        }))
        assert result["status"] == "error"
        assert f"{field} must be an integer" in result["error"]


def test_process_manage_wait_timeout_string_is_validated():
    registry = ProcessRegistry()
    invalid = registry.wait("proc_missing", timeout="soon")
    assert invalid["status"] == "error"
    assert "timeout must be an integer" in invalid["error"]
    zero = registry.wait("proc_missing", timeout="0")
    assert zero["status"] == "error"
    assert "timeout must be positive" in zero["error"]
