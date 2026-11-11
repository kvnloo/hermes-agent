"""Waiting for a native vault card is not browser inactivity."""

import json
from types import SimpleNamespace

import pytest

from gateway.config import Platform
from gateway.session_events import SessionEvents
from gateway.session_server_requests import resolve
from gateway.session_vault_prompt import vault_prompt_scope
from hermes_constants import hermes_home_key
from tests.waiting import wait_until
from tools import browser_session as bs
from tools import browser_session_lifecycle as lifecycle
from tools import browser_vault_tool as vault
from tools.registry import registry


class _Peer:
    def __init__(self):
        self.frames = []

    def write(self, frame):
        self.frames.append(frame)
        return True

    def close(self):
        pass


@pytest.fixture
def idle_browser(monkeypatch):
    for name in ("_active_sessions", "_session_last_activity", "_session_owner_homes", "_cleanup_failures"):
        monkeypatch.setattr(bs, name, {})
    clock = [1000.0]
    monkeypatch.setattr(lifecycle, "time", SimpleNamespace(time=lambda: clock[0]))
    monkeypatch.setattr(bs, "BROWSER_SESSION_INACTIVITY_TIMEOUT", 120)
    monkeypatch.setattr(bs, "human_holds_shared_browser", lambda info: False)
    monkeypatch.setattr(lifecycle, "release_session_backend", lambda *args: None)
    monkeypatch.setattr("tools.browser_session_cdp.stop_cdp_supervisor", lambda *args: None)
    home = hermes_home_key()
    info = {"home_key": home, "cdp_url": "ws://127.0.0.1:9222/devtools/browser/test", "features": {}}
    bs._active_sessions["otp-task"] = info
    lifecycle.update_session_activity("otp-task")
    bs._active_sessions["other-task"] = dict(info, cdp_url="ws://127.0.0.1:9223/devtools/browser/other")
    lifecycle.update_session_activity("other-task")
    return clock, info


@pytest.mark.parametrize("answer", ["763921", ""])
def test_native_vault_card_outlives_idle_timeout_and_releases_after_answer(idle_browser, monkeypatch, answer):
    clock, info = idle_browser
    controls = [{"index": 0, "type": "text", "name": "otp", "autocomplete": "one-time-code"}]
    monkeypatch.setattr(vault, "_focus_bound_origin", lambda *args: None)
    monkeypatch.setattr(vault, "_eval_js", lambda task, expr: {
        "success": True, "result": json.dumps(controls) if "querySelectorAll" in expr else "https://example.com/otp",
    })
    filled = []

    def write(task, expression):
        # The answer arriving must not open a gap between retention and the secret write.
        lifecycle.cleanup_inactive_sessions()
        assert bs._active_sessions.get(task) is info
        filled.append(expression)
        return {"success": True, "result": json.dumps({"filled": 1})}

    monkeypatch.setattr(vault, "_eval_js_secret", write)
    events, peer = SessionEvents(), _Peer()
    events.fanout.attach(peer)
    authority = SimpleNamespace(sessions={"otp-task": SimpleNamespace(event_stream=events)})
    turn = SimpleNamespace(_approval_owner=(authority, "otp-task", 1),
                           _ctx=SimpleNamespace(source=SimpleNamespace(platform=Platform.LOCAL)))
    result = {}

    def run():
        with vault_prompt_scope(turn, SimpleNamespace()):
            result["raw"] = registry.dispatch("browser_vault", {"action": "enter_code"}, task_id="otp-task")

    from agent.memory_provider import spawn_context_thread
    worker = spawn_context_thread(target=run, name="vault-card-test")
    worker.start()
    request = None
    try:
        wait_until(lambda: any(f.get("method") == "vault.code" for f in peer.frames), what="native vault card")
        request = next(f for f in peer.frames if f.get("method") == "vault.code")
        clock[0] += 150
        lifecycle.cleanup_inactive_sessions()
        assert bs._active_sessions.get("otp-task") is info
        assert "other-task" not in bs._active_sessions
    finally:
        if request:
            resolve({"jsonrpc": "2.0", "id": request["id"], "result": {"value": answer}})
        worker.join(5)
    assert not worker.is_alive()
    output = json.loads(result["raw"])
    assert output["success"] is bool(answer)
    assert bool(filled) is bool(answer)
    if answer:
        assert answer not in result["raw"] and answer not in repr(peer.frames)
    else:
        assert output["error_type"] == "code_declined"
    clock[0] += 121
    lifecycle.cleanup_inactive_sessions()
    assert "otp-task" not in bs._active_sessions


@pytest.mark.parametrize("case", [
    "nested", "exception", "explicit-close", "replacement", "claimed", "stale-snapshot",
    "other-profile", "named", "sidecar", "plugin",
    "qualified-without-supervisor", "sidecar-without-supervisor", "replacement-after-claim",
])
def test_vault_retention_lifecycle_boundaries(idle_browser, monkeypatch, case):
    clock, info = idle_browser
    key = "otp-task"
    if case == "replacement-after-claim":
        _replace_after_claim(clock, info, monkeypatch)
        return
    if case in {"qualified-without-supervisor", "sidecar-without-supervisor"}:
        _retain_exact_key(clock, info, case)
        return
    if case in {"named", "sidecar"}:
        from tools.browser_supervisor import SUPERVISOR_REGISTRY
        key = "bu-named-browser@" + hermes_home_key() + ("::local" if case == "sidecar" else "")
        bs._active_sessions[key] = bs._active_sessions.pop("otp-task")
        bs._session_last_activity[key] = bs._session_last_activity.pop("otp-task")
        bs._session_owner_homes[key] = bs._session_owner_homes.pop("otp-task")
        monkeypatch.setattr(SUPERVISOR_REGISTRY, "_by_task", {"otp-task": SimpleNamespace(cdp_url=info["cdp_url"])})
        monkeypatch.setattr(SUPERVISOR_REGISTRY, "_home_by_task", {"otp-task": hermes_home_key()})
    if case == "other-profile":
        bs._active_sessions["otp-task@foreign"] = dict(info, home_key="foreign")
        bs._session_last_activity["otp-task@foreign"] = clock[0]
    if case == "plugin":
        monkeypatch.setattr(vault, "_page_backend", lambda task: object())

    def while_retained():
        clock[0] += 150
        if case == "nested":
            assert vault._fenced_page_op("otp-task", lambda: "nested") == "nested"
            clock[0] += 150
        lifecycle.cleanup_inactive_sessions()
        if case == "plugin":
            assert key not in bs._active_sessions
            return "plugin"
        assert bs._active_sessions.get(key) is info
        assert "other-task" not in bs._active_sessions
        if case == "other-profile":
            assert "otp-task@foreign" not in bs._active_sessions
        if case == "exception":
            raise ValueError("synthetic prompt failure")
        if case == "explicit-close":
            lifecycle.cleanup_single_session(key)
        if case == "replacement":
            bs._active_sessions[key] = {"home_key": hermes_home_key(), "features": {}}
            bs._session_last_activity[key] = clock[0] - 200
        return "finished"

    if case == "exception":
        with pytest.raises(ValueError, match="synthetic prompt failure"):
            vault._fenced_page_op("otp-task", while_retained)
    elif case == "claimed":
        clock[0] += 150
        with lifecycle._claim_idle_session(key) as claimed:
            assert claimed
            result = json.loads(vault._fenced_page_op("otp-task", lambda: pytest.fail("admitted during cleanup")))
            assert result["error_type"] == "browser_closing"
    elif case == "stale-snapshot":
        clock[0] += 150

        def after_snapshot(candidate):
            if candidate == key:
                assert vault._fenced_page_op("otp-task", lambda: "finished") == "finished"
            return False

        monkeypatch.setattr(lifecycle, "_human_holds_shared_browser", after_snapshot)
        lifecycle.cleanup_inactive_sessions()
        assert bs._active_sessions.get(key) is info
        monkeypatch.setattr(lifecycle, "_human_holds_shared_browser", lambda key: False)
    else:
        vault._fenced_page_op("otp-task", while_retained)
    if case == "explicit-close":
        assert key not in bs._active_sessions and key not in bs._session_last_activity
    if case == "replacement":
        assert bs._session_last_activity[key] == clock[0] - 200
    assert not info.get("_vault_holds")
    clock[0] += 121
    lifecycle.cleanup_inactive_sessions()
    assert key not in bs._active_sessions


def _retain_exact_key(clock, info, case):
    key = "otp-task@" + hermes_home_key() + ("::local" if case.startswith("sidecar") else "")
    bs._active_sessions[key] = bs._active_sessions.pop("otp-task")
    bs._session_last_activity[key] = bs._session_last_activity.pop("otp-task")
    bs._session_owner_homes[key] = bs._session_owner_homes.pop("otp-task")

    def waiting():
        clock[0] += 150
        lifecycle.cleanup_inactive_sessions()
        assert bs._active_sessions.get(key) is info
        return "finished"

    assert vault._fenced_page_op(key, waiting) == "finished"
    clock[0] += 121
    lifecycle.cleanup_inactive_sessions()
    assert key not in bs._active_sessions


def _replace_after_claim(clock, info, monkeypatch):
    from tools.browser_supervisor import SUPERVISOR_REGISTRY
    replacement_supervisor = SimpleNamespace(cdp_url=info["cdp_url"])
    monkeypatch.setattr(SUPERVISOR_REGISTRY, "_by_task", {})
    monkeypatch.setattr(SUPERVISOR_REGISTRY, "_home_by_task", {})
    cleanup = lifecycle._cleanup_one_inactive
    replacement = dict(info)
    seen = []

    def after_claim(key, elapsed, **kwargs):
        if key != "otp-task":
            return cleanup(key, elapsed, **kwargs)
        lifecycle.cleanup_single_session(key)
        bs._active_sessions[key] = replacement
        lifecycle.update_session_activity(key)
        SUPERVISOR_REGISTRY._by_task[key] = replacement_supervisor
        SUPERVISOR_REGISTRY._home_by_task[key] = hermes_home_key()

        def new_prompt():
            cleanup(key, elapsed, **kwargs)
            assert bs._active_sessions.get(key) is replacement
            assert SUPERVISOR_REGISTRY.get(key) is replacement_supervisor
            seen.append(True)
            return "finished"

        assert vault._fenced_page_op(key, new_prompt) == "finished"

    monkeypatch.setattr(lifecycle, "_cleanup_one_inactive", after_claim)
    clock[0] += 150
    lifecycle.cleanup_inactive_sessions()
    assert seen == [True]
    assert not replacement.get("_vault_holds")
    monkeypatch.setattr(lifecycle, "_cleanup_one_inactive", cleanup)
    SUPERVISOR_REGISTRY._by_task.clear()
    clock[0] += 121
    lifecycle.cleanup_inactive_sessions()
    assert "otp-task" not in bs._active_sessions


@pytest.mark.parametrize("case", ["closing-admission", "failure-after-replacement", "failure-retry"])
def test_claimed_disposal_preserves_admission_and_failure_ownership(idle_browser, monkeypatch, case):
    from tools.browser_supervisor import SUPERVISOR_REGISTRY
    clock, info = idle_browser
    seen = []

    def stop():
        result = json.loads(vault._fenced_page_op("otp-task", lambda: pytest.fail("admitted while closing")))
        assert result["error_type"] == "browser_closing"
        seen.append("refused")

    supervisor = SimpleNamespace(cdp_url=info["cdp_url"], stop=stop)
    monkeypatch.setattr(SUPERVISOR_REGISTRY, "_by_task", {"otp-task": supervisor})
    monkeypatch.setattr(SUPERVISOR_REGISTRY, "_home_by_task", {"otp-task": hermes_home_key()})
    replacement = dict(info)

    def release(key, record):
        if key != "otp-task" or case == "closing-admission":
            return
        if case == "failure-after-replacement":
            bs._active_sessions[key] = replacement
            lifecycle.update_session_activity(key)
        raise RuntimeError("synthetic teardown failure")

    monkeypatch.setattr(lifecycle, "release_session_backend", release)
    clock[0] += 150
    lifecycle.cleanup_inactive_sessions()
    assert seen == ["refused"]
    if case == "closing-admission":
        assert "otp-task" not in bs._active_sessions
    elif case == "failure-after-replacement":
        assert bs._active_sessions["otp-task"] is replacement
        assert bs._session_last_activity["otp-task"] == clock[0]
        assert "otp-task" not in bs._cleanup_failures
    else:
        assert bs._active_sessions["otp-task"] is info
        assert bs._cleanup_failures["otp-task"] == 1
        assert not info.get("_idle_cleanup")
        monkeypatch.setattr(lifecycle, "release_session_backend", lambda *args: None)
        lifecycle.cleanup_inactive_sessions()
        assert "otp-task" not in bs._active_sessions
        assert "otp-task" not in bs._cleanup_failures
