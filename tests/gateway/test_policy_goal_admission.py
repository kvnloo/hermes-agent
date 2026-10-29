"""Policy continuations must reach the native FIFO without surviving owner controls."""
import shlex
import sys
from unittest.mock import AsyncMock

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_cli.goals import GoalGate, GoalManager, load_goal
from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest
from tests.gateway.test_session_end_delegations import _admissions, _local, _record_turns
from tests.hermes_cli.test_goal_policy import Policy, judge


async def setup_goal(tmp_path, monkeypatch):
    runner, authority, ref, _actor = await _local(tmp_path, monkeypatch)
    plugins = PluginManager()
    plugins._discovered = True
    ctx = PluginContext(PluginManifest(name="test-policy"), plugins)
    monkeypatch.setattr(ctx, "get_config", lambda key, default=None: True if key == "allow_arm" else default)
    monkeypatch.setattr("hermes_cli.plugins.get_plugin_manager", lambda: plugins)
    ctx.register_goal_policy(Policy())
    live = authority.sessions[ref.session_id]
    entry = runner.session_store.lookup_by_session_key(live.route)
    assert entry is not None
    with scoped_current_session_id(entry.session_id):
        ctx.arm_goal("Finish the fixture", max_turns=8,
                     gates=[GoalGate(f"{shlex.quote(sys.executable)} -c 'print(1)'")])
    judge(monkeypatch)
    return runner, authority, ref, live.source, entry


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, RuntimeError("transport disconnected")])
async def test_refused_local_continuation_is_visible_and_resumable(tmp_path, monkeypatch, failure):
    runner, authority, ref, source, entry = await setup_goal(tmp_path, monkeypatch)
    from gateway import session_automation
    admit = session_automation.admit_route_wake
    monkeypatch.setattr(Policy, "prepare", lambda self: "New required workflow after context loss.")
    notices = []
    monkeypatch.setattr(runner, "_defer_goal_status_notice_after_delivery", AsyncMock(side_effect=lambda s, m: notices.append(m)))
    monkeypatch.setattr(session_automation, "admit_route_wake",
                        AsyncMock(side_effect=failure) if isinstance(failure, Exception) else AsyncMock(return_value=False))
    try:
        await runner._post_turn_goal_continuation(session_entry=entry, source=source, final_response="unfinished")
        state = load_goal(entry.session_id)
        assert state is not None and state.paused_reason is not None
        assert state.status == "paused"
        assert "admission" in state.paused_reason.lower()
        assert any("resume" in m.lower() for m in notices)
        assert not _admissions(authority, ref)
        monkeypatch.setattr(session_automation, "admit_route_wake", admit)
        GoalManager(entry.session_id).resume()
        await runner._post_turn_goal_continuation(session_entry=entry, source=source, final_response="reconnected")
        assert len(_admissions(authority, ref)) == 1
        seen = _record_turns(runner)
        await authority._drain(ref)
        assert len(seen) == 1 and "Finish the fixture" in seen[0]
        assert "New required workflow after context loss." in seen[0]
    finally:
        authority.db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("control", ["pause", "clear"])
async def test_queued_policy_continuation_cannot_outlive_control(tmp_path, monkeypatch, control):
    runner, authority, ref, source, entry = await setup_goal(tmp_path, monkeypatch)
    try:
        await runner._post_turn_goal_continuation(session_entry=entry, source=source, final_response="unfinished")
        assert len(_admissions(authority, ref)) == 1
        getattr(GoalManager(entry.session_id), control)()
        seen = _record_turns(runner)
        await authority._drain(ref)
        assert seen == []
        stored = load_goal(entry.session_id)
        assert stored is not None
        assert stored.status == ("paused" if control == "pause" else "cleared")
    finally:
        authority.db.close()


@pytest.mark.asyncio
async def test_local_reconnect_restores_owned_route_before_admission(tmp_path, monkeypatch):
    runner, authority, ref, source, entry = await setup_goal(tmp_path, monkeypatch)
    authority.sessions.pop(ref.session_id)
    try:
        await runner._post_turn_goal_continuation(session_entry=entry, source=source, final_response="unfinished")
        rows = _admissions(authority, ref)
        assert len(rows) == 1 and rows[0]["status"] == "queued"
        seen = _record_turns(runner)
        await authority._drain(ref)
        assert len(seen) == 1
    finally:
        authority.db.close()
