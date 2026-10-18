"""Adapter contracts for #576. Fake CLI/page tests do NOT certify native Tern."""
import json
import subprocess
from unittest.mock import Mock

import pytest

from tools import browser_tern as tern
from tools.browser_tern_transport import TernBrowserCLI


@pytest.fixture
def page(monkeypatch):
    calls = []

    def request(op):
        calls.append(op)
        return {"block": 8, "url": "https://example.org/", "title": "Page", "value": 42}

    provider = tern.TernBrowserProvider(request, 3)
    provider.targets["task"] = tern.Target(8, True)
    monkeypatch.setattr(tern, "_providers", {(tern.hermes_home_key(), "window"): provider})
    monkeypatch.setattr(tern, "get_provider", lambda: provider)
    return provider, calls


def test_frame_selection_is_verified_and_eval_uses_exact_native_frame(page):
    provider, calls = page
    assert provider.select_frame("task", "8", "1.0")["frame"] == "1.0"
    result = provider.command("task", "eval", ["6 * 7"])
    assert result["data"]["result"] == 42
    assert result["tern_target"]["frame"] == "1.0"
    assert [op.get("frame") for op in calls if op["op"] == "eval"] == ["1.0", "1.0"]
    for command, args in [("snapshot", []), ("click", ["@e1"]), ("screenshot", []), ("open", ["https://other.org/"])]:
        count = len(calls)
        assert tern.run_command("task", command, args)["error_kind"] == "unsupported"
        assert len(calls) == count  # Never silently act on main instead.
    assert "frame" not in provider.select_frame("task", "8", "main")
    assert "frame" not in provider.command("task", "eval", ["1"])["tern_target"]
    assert "frame" not in next(op for op in reversed(calls) if op["op"] == "eval")


@pytest.mark.parametrize("frame", [" 0", "00", "+0", "1.", "0..1", "Main", "main\n", 0, None])
def test_malformed_frames_never_reach_the_page(page, frame):
    provider, calls = page
    with pytest.raises(tern.TernBrowserError):
        provider.select_frame("task", "8", frame)
    assert calls == []


def test_detached_frame_or_page_exception_preserves_ownership_and_selection(page):
    provider, _ = page
    provider.select_frame("task", "8", "0")
    provider.request = Mock(side_effect=tern.TernBrowserError("Frame detached", "not_found"))
    with pytest.raises(tern.TernBrowserError):
        provider.select_frame("task", "8", "1")
    assert provider.owned("task").frame == "0"
    assert tern.run_command("task", "eval", ["1"])["error_kind"] == "not_found"
    assert provider.owned("task").block == 8


@pytest.mark.parametrize("command,args", [("console", []), ("record", ["start"]), ("screenshot", ["--annotate"])])
def test_undocumented_commands_fail_closed_without_native_call(page, command, args):
    _, calls = page
    result = tern.run_command("task", command, args)
    assert result["success"] is False
    assert result["error_kind"] == "unsupported"
    assert calls == []


def test_page_failure_is_not_a_capability_failure_or_fallback(page):
    provider, _ = page
    provider.targets.clear()
    def request(op):
        if op["op"] == "open":
            return {"block": 9}
        if op["op"] == "snapshot":
            raise tern.TernBrowserError("Page crashed", "failed")
        return {}
    provider.request = request
    assert tern.run_command("task", "open", ["https://example.org/"])["error_kind"] == "failed"
    assert not provider.targets
    assert tern.get_provider() is provider


def test_transport_loss_never_reroutes_an_owned_task(page, monkeypatch):
    provider, calls = page
    monkeypatch.setattr(tern, "get_provider", lambda: None)
    assert tern.run_command("task", "snapshot", [])["error_kind"] == "ownership"
    assert calls == []
    assert provider.owned("task").block == 8


def test_release_requires_exact_owner_and_acknowledged_cleanup(page):
    provider, calls = page
    with pytest.raises(tern.TernBrowserError):
        provider.release_by_user("other", "8")
    provider.request = Mock(side_effect=tern.TernBrowserError("disconnected", "closed_transport"))
    with pytest.raises(tern.TernBrowserError):
        provider.release_by_user("task", "8")
    assert provider.owned("task").adopted
    provider.request = lambda op: calls.append(op) or {}
    assert provider.release_by_user("task", "8") == {"target_id": "8", "released": True}
    assert calls == [{"op": "release", "block": 8}]
    assert not provider.targets


def test_late_open_closes_only_its_exact_answer_never_a_discovery_candidate(monkeypatch):
    calls = []
    process = Mock()
    process.communicate.side_effect = [subprocess.TimeoutExpired("tern", 0.01), ('{"ok":{"block":19}}', '')]
    process.poll.side_effect = [None, 0]
    process.returncode = 0
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=process))
    transport = TernBrowserCLI("/owned/tern", {"PATH": "/owned"}, "window", timeout=0.01)
    transport.invoke = lambda argv: calls.append(json.loads(argv[1])) or {"blocks": [{"block": 99, "owner": 3}]}
    provider = tern.TernBrowserProvider(transport, 3)
    monkeypatch.setattr(tern, "_providers", {(tern.hermes_home_key(),): provider})
    monkeypatch.setattr(tern, "get_provider", lambda: provider)
    assert tern.run_command("task", "open", ["https://example.org/"])["error_kind"] == "open_pending"
    assert tern.run_command("other", "open", ["https://other.org/"])["error_kind"] == "open_pending"
    assert calls == []
    tern.cleanup("task")
    assert calls == [{"op": "close", "block": 19}]
    assert provider.pending_open is None
    assert not provider.targets
    process.kill.assert_not_called()
    argv = subprocess.Popen.call_args.args[0]
    assert argv[-2:] == ["--window", "window"]
    assert subprocess.Popen.call_args.kwargs["env"] == {"PATH": "/owned"}


@pytest.mark.parametrize("returncode,stdout", [(124, ""), (0, "not JSON"), (1, '{"error":{"kind":"closed","message":"disconnected"}}')])
def test_indeterminate_open_retains_quarantine_after_cli_exit(monkeypatch, returncode, stdout):
    process = Mock(returncode=returncode)
    process.communicate.return_value = (stdout, "")
    monkeypatch.setattr(subprocess, "Popen", Mock(return_value=process))
    transport = TernBrowserCLI("/owned/tern", {}, "window")
    provider = tern.TernBrowserProvider(transport, 3)
    monkeypatch.setattr(tern, "_providers", {(tern.hermes_home_key(),): provider})
    monkeypatch.setattr(tern, "get_provider", lambda: provider)
    assert tern.run_command("task", "open", ["https://example.org/"])["success"] is False
    assert tern.run_command("task", "open", ["https://example.org/"])["error_kind"] == "open_unknown"
    tern.cleanup()
    assert provider.pending_open == "task"
    assert tern._providers
    assert subprocess.Popen.call_count == 1


def test_handover_probe_disconnect_retains_cleanup_claim_without_drive_permission(page):
    provider, calls = page
    def request(op):
        calls.append(op)
        if op["op"] == "blocks":
            return {"blocks": [{"block": 9, "driven": False}]}
        raise tern.TernBrowserError("disconnected", "transport")
    provider.request = request
    with pytest.raises(tern.TernBrowserError):
        provider.adopt_by_user("task", "9")
    assert provider.owned("task").block == 8
    assert provider.pending_releases == {9: "task"}
    assert provider._taken(9)
    assert tern.run_command("task", "eval", ["1"])["error_kind"] == "ownership"
    provider.request = lambda op: calls.append(op) or {}
    tern.cleanup("task")
    assert not provider.pending_releases
    assert {"op": "release", "block": 9} in calls
    assert not any(op["op"] == "close" for op in calls)


def test_pending_open_is_fenced_across_profiles_in_one_window(page, monkeypatch):
    provider, calls = page
    provider.ownership_scope = ("window", "socket")
    provider.pending_open = "task"
    peer = tern.TernBrowserProvider(provider.request, 4, ownership_scope=provider.ownership_scope)
    monkeypatch.setitem(tern._providers, ("another-profile",), peer)
    with pytest.raises(tern.TernBrowserError, match="indeterminate"):
        peer.open("other")
    assert calls == []


def test_existing_console_tool_preserves_frame_identity_and_native_error_kind(page, monkeypatch):
    from tools import browser_tool as browser
    provider, _ = page
    monkeypatch.setattr(browser, "_last_session_key", lambda task: task)
    monkeypatch.setattr(browser, "_is_camofox_mode", lambda: False)
    monkeypatch.setattr(browser, "_eval_supervisor_fast_path", lambda *args: None)
    monkeypatch.setattr(browser._eval_policy, "_eval_ssrf_guard_active", lambda task: False)
    provider.select_frame("task", "8", "1.0")
    result = json.loads(browser.browser_console(expression="6 * 7", task_id="task"))
    assert result["result"] == 42
    assert result["tern_target"]["frame"] == "1.0"
    provider.request = Mock(side_effect=tern.TernBrowserError("Function not found in page", "js"))
    result = json.loads(browser.browser_console(expression="missing()", task_id="task"))
    assert result["error_kind"] == "js"
    assert result["error"] == "Function not found in page"
    assert json.loads(browser.browser_console(task_id="task"))["error_kind"] == "unsupported"


def test_real_cli_process_survives_outer_timeout_and_late_answer_is_reaped(tmp_path):
    """Real subprocess lifecycle with a labelled stub CLI, not a native page."""
    import sys
    executable = tmp_path / "stub-tern"
    gate, log = tmp_path / "gate", tmp_path / "calls.jsonl"
    executable.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys, time
op = json.loads(sys.argv[2])
with open(os.environ["LOG"], "a") as log:
    log.write(json.dumps({"op": op, "argv": sys.argv[1:]}) + "\\n")
if op["op"] == "open":
    deadline = time.monotonic() + 5
    while not pathlib.Path(os.environ["GATE"]).exists():
        if time.monotonic() > deadline:
            sys.exit(124)
        time.sleep(0.01)
print(json.dumps({"ok": {"block": 73}}), flush=True)
''')
    executable.chmod(0o700)
    transport = TernBrowserCLI(str(executable), {"GATE": str(gate), "LOG": str(log)}, "isolated-window", timeout=0.01)
    provider = tern.TernBrowserProvider(transport, 3)
    try:
        with pytest.raises(tern.TernBrowserError) as failed:
            provider.open("task")
        assert failed.value.kind == "open_pending"
        process = transport.pending
        assert process is not None and process.poll() is None
        gate.touch()
        assert process.wait(timeout=10) == 0
        # Use a normal subprocess wait budget for the cleanup request.
        transport.timeout = 10
        provider.reconcile_open()
        assert provider.pending_open is None
        assert transport.pending is None
        entries = [json.loads(line) for line in log.read_text().splitlines()]
        assert [entry["op"] for entry in entries] == [
            {"op": "open", "owner": 3, "url": "about:blank"}, {"op": "close", "block": 73}]
        assert all(entry["argv"][-2:] == ["--window", "isolated-window"] for entry in entries)
    finally:
        gate.touch()
        if transport.pending is not None:
            transport.pending.communicate(timeout=10)


def test_explicit_cdp_override_precedes_native_discovery(monkeypatch):
    from tools import browser_tool_cdp
    from tools.environments import local
    monkeypatch.setattr(local, "served_profile_child_env", lambda **kwargs: {
        "TERN_PANE": "3", "TERN_WINDOW_KEY": "isolated-window", "PATH": "/owned/bin"})
    monkeypatch.setattr(browser_tool_cdp, "_get_cdp_override_raw", lambda: "http://127.0.0.1:9222")
    spawn = Mock(side_effect=AssertionError("CDP selection must not probe native pages"))
    monkeypatch.setattr(tern.subprocess, "run", spawn)
    assert tern._context() is None
    spawn.assert_not_called()
