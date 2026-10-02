"""The TUI exit epilogue must stay quiet when a late KeyboardInterrupt lands in it.

``_print_tui_exit_summary`` runs after the TUI process has already exited; a
second Ctrl+C arriving during its read-only DB/config load used to escape
``except Exception`` (KeyboardInterrupt is a BaseException) and dump a raw
traceback into the shell — same class as #83341 / #80256.
"""

import pytest

import hermes_state
import hermes_cli.main as hermes_main
from hermes_cli.main_tui_launch import _print_tui_exit_summary


def _raise_interrupt(*args, **kwargs):
    raise KeyboardInterrupt


def test_exit_summary_swallows_keyboard_interrupt_from_db_read(monkeypatch):
    monkeypatch.setattr(hermes_state, "SessionDB", _raise_interrupt)

    # Must return quietly — the TUI already exited; no traceback may reach the shell.
    _print_tui_exit_summary("20260927_134833_9d0de4ee")


def test_exit_summary_swallows_keyboard_interrupt_from_last_session_lookup(monkeypatch):
    monkeypatch.setattr(hermes_main, "_resolve_last_session", _raise_interrupt)

    _print_tui_exit_summary(None)


@pytest.mark.parametrize("stage,child_code,error_kind", [
    ("close", 0, "interrupt"),
    ("close", 130, "interrupt"),
    ("profile", 0, "interrupt"),
    ("profile", 130, "interrupt"),
    ("print", 0, "interrupt"),
    ("print", 130, "interrupt"),
    ("unused", 7, "interrupt"),
    ("close", 0, "ordinary"),
], ids=["close-success", "close-interrupted-child", "profile-success", "profile-interrupted-child",
        "print-success", "print-interrupted-child", "failed-child-control", "ordinary-error-control"])
def test_launcher_preserves_child_status_after_late_epilogue_interrupt(
        monkeypatch, tmp_path, record_property, stage, child_code, error_kind):
    """Late Ctrl+C at the only production caller must not replace the settled child status."""
    import json
    import tempfile
    from pathlib import Path

    import hermes_cli.main_tui_launch as launcher
    import hermes_cli.profiles as profiles
    import hermes_cli.shared_session_attach as attachment
    import tools.environments.local as local

    calls = {"child": 0, "db_open": 0, "db_close": 0, "profile": 0, "print": 0}
    active_files = []

    def fail_here():
        if error_kind == "interrupt":
            raise KeyboardInterrupt
        raise ValueError("ordinary epilogue error")

    class ReadOnlyDB:
        def __init__(self, **kwargs):
            assert kwargs == {"read_only": True}
            calls["db_open"] += 1

        def get_session(self, session_id):
            assert session_id == "fixture-session"
            return {"message_count": 1}

        def get_session_title(self, _session_id):
            return ""

        def close(self):
            calls["db_close"] += 1
            if stage == "close":
                fail_here()

    def profile():
        calls["profile"] += 1
        if stage == "profile":
            fail_here()
        return "default"

    def output(*_args, **_kwargs):
        calls["print"] += 1
        if stage == "print":
            fail_here()

    def child(_argv, *, cwd, env):
        calls["child"] += 1
        active = Path(env["HERMES_TUI_ACTIVE_SESSION_FILE"])
        assert active.is_file() and active.parent == tmp_path
        active_files.append(active)
        assert cwd == str(tmp_path)
        return child_code

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(local, "build_subprocess_env", lambda **_kwargs: {"TERMINAL_ENV": "local"})
    monkeypatch.setattr(attachment, "configure_tui_attachment", lambda *_args: None)
    monkeypatch.setattr(launcher, "_apply_tui_python_env", lambda _env: None)
    monkeypatch.setattr(launcher, "_make_tui_argv", lambda *_args: (["fixture-tui"], tmp_path))
    monkeypatch.setattr(launcher.subprocess, "call", child)
    monkeypatch.setattr(hermes_state, "SessionDB", ReadOnlyDB)
    monkeypatch.setattr(profiles, "get_active_profile_name", profile)
    monkeypatch.setattr(launcher, "print", output, raising=False)

    outcome = None
    try:
        launcher._launch_tui(resume_session_id="fixture-session", native_mode=False)
    except SystemExit as exc:
        outcome = {"kind": "exit", "code": exc.code}
    except KeyboardInterrupt:
        outcome = {"kind": "interrupt"}
    except ValueError as exc:
        outcome = {"kind": "ordinary", "message": str(exc)}
    observation = {"stage": stage, "child_code": child_code, "calls": calls, "outcome": outcome,
                   "active_files_removed": bool(active_files) and all(not p.exists() for p in active_files)}
    record_property("tui_exit_observation", json.dumps(observation, sort_keys=True))

    assert observation["active_files_removed"]
    expected_calls = {"child": 1, "db_open": int(child_code != 7), "db_close": int(child_code != 7),
                      "profile": int(stage in ("profile", "print") and child_code != 7),
                      "print": int(stage == "print" and child_code != 7)}
    assert calls == expected_calls
    expected = ({"kind": "ordinary", "message": "ordinary epilogue error"} if error_kind == "ordinary"
                else {"kind": "exit", "code": child_code})
    assert outcome == expected
