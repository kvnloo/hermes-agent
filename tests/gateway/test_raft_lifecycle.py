"""Raft lifecycle regressions independent of the optional HTTP transport dependency.

Adapted from Detail's downstream #44; real adapter hooks, no service or CLI.
"""

import pytest

from gateway.config import PlatformConfig
import plugins.platforms.raft.adapter as raft_mod
from plugins.platforms.raft.adapter import (
    _RAFT_CONTEXT_LOCK,
    _RAFT_PROMPT_TURN_IDS,
    _RAFT_SESSION_IDS,
    _RAFT_TURN_IDS,
    _is_raft_context,
    _on_session_start,
    _on_pre_llm_call,
    _on_session_end,
    _on_session_finalize,
)


def _make_adapter():
    return raft_mod.RaftAdapter(PlatformConfig(enabled=True, extra={
        "bridge_token": "fixture-token", "runtime_session": "default", "port": 0,
    }))


class TestRaftContextTracking:
    """Per-session turn-id tracking so the gateway teardown path releases
    every turn id the session registered instead of leaking it into the
    module-global turn-id sets."""

    @pytest.fixture(autouse=True)
    def _reset_raft_context(self):
        with _RAFT_CONTEXT_LOCK:
            _RAFT_SESSION_IDS.clear()
            _RAFT_TURN_IDS.clear()
            _RAFT_PROMPT_TURN_IDS.clear()
            getattr(raft_mod, "_RAFT_SESSION_TURNS", {}).clear()
        yield
        with _RAFT_CONTEXT_LOCK:
            _RAFT_SESSION_IDS.clear()
            _RAFT_TURN_IDS.clear()
            _RAFT_PROMPT_TURN_IDS.clear()
            getattr(raft_mod, "_RAFT_SESSION_TURNS", {}).clear()

    @staticmethod
    def _drive_session_turn(session_id, turn_id):
        _on_session_start(platform="raft", session_id=session_id)
        _on_pre_llm_call(platform="raft", session_id=session_id, turn_id=turn_id)

    def test_gateway_teardown_without_turn_id_releases_all_turn_ids(self):
        """The reported bug: gateway _finalize_session fires on_session_end
        and on_session_finalize WITHOUT a turn_id (force-reaped in-flight
        turn). The session-registered turn id must not leak."""
        self._drive_session_turn("gw-7", "gw-7:task-1:deadbeef")

        # Sanity: turn id registered across all three sets before teardown.
        assert _RAFT_TURN_IDS == {"gw-7:task-1:deadbeef"}
        assert _RAFT_PROMPT_TURN_IDS == {"gw-7:task-1:deadbeef"}
        assert _RAFT_SESSION_IDS == {"gw-7"}

        # Gateway teardown sequence: both hooks fire without a turn_id.
        _on_session_end(
            platform="raft", session_id="gw-7", completed=False, interrupted=True
        )
        _on_session_finalize(platform="raft", session_id="gw-7")

        assert _RAFT_TURN_IDS == set()
        assert _RAFT_PROMPT_TURN_IDS == set()
        assert _RAFT_SESSION_IDS == set()

    def test_repeated_sessions_do_not_accumulate_orphaned_turn_ids(self):
        """Several sessions ending via the no-turn_id teardown path must not
        leave any turn id behind — the leak-rate defect the fix targets."""
        for s in range(4):
            sid = f"gw-{s}"
            self._drive_session_turn(sid, f"{sid}:task:deadbeef")
            _on_session_end(platform="raft", session_id=sid, completed=False, interrupted=True)
            _on_session_finalize(platform="raft", session_id=sid)

        assert _RAFT_TURN_IDS == set()
        assert _RAFT_PROMPT_TURN_IDS == set()
        assert _RAFT_SESSION_IDS == set()

    def test_concurrent_sessions_finalize_independently(self):
        """Draining one session must not touch another session's turn ids."""
        self._drive_session_turn("gw-7", "turn-a")
        self._drive_session_turn("gw-9", "turn-b")

        # Finalize only gw-7 via the no-turn_id teardown path.
        _on_session_end(platform="raft", session_id="gw-7", completed=False, interrupted=True)
        _on_session_finalize(platform="raft", session_id="gw-7")

        assert _RAFT_TURN_IDS == {"turn-b"}
        assert _RAFT_PROMPT_TURN_IDS == {"turn-b"}
        assert _RAFT_SESSION_IDS == {"gw-9"}

    def test_normal_per_turn_finalize_then_session_finalize_clears_all(self):
        """No regression: the normal path (per-turn on_session_end WITH a
        turn_id then on_session_finalize without) still cleans everything."""
        self._drive_session_turn("gw-7", "turn-1")

        _on_session_end(platform="raft", session_id="gw-7", turn_id="turn-1", completed=True)
        # After per-turn end: turn id gone from the two turn-id sets, session
        # still tracked until the explicit finalize.
        assert _RAFT_TURN_IDS == set()
        assert _RAFT_PROMPT_TURN_IDS == set()
        assert _RAFT_SESSION_IDS == {"gw-7"}

        _on_session_finalize(platform="raft", session_id="gw-7")
        assert _RAFT_SESSION_IDS == set()

    def test_pre_llm_call_dedup_unchanged_within_a_turn(self, monkeypatch):
        """Only the first call per turn emits the existing activity event."""
        import weakref

        adapter = _make_adapter()
        monkeypatch.setattr(raft_mod, "_ACTIVE_ADAPTERS", weakref.WeakSet([adapter]))
        _on_pre_llm_call(platform="raft", session_id="gw-7", turn_id="turn-1")
        _on_pre_llm_call(platform="raft", session_id="gw-7", turn_id="turn-1")
        _on_pre_llm_call(platform="raft", session_id="gw-7", turn_id="turn-2")
        events = adapter._activity_queue.drain()["events"]
        assert [event["hookEventName"] for event in events] == ["UserPromptSubmit", "UserPromptSubmit"]
        assert _RAFT_PROMPT_TURN_IDS == {"turn-1", "turn-2"}

    def test_non_raft_session_hooks_do_not_mutate_raft_tracking_state(self):
        """A non-raft platform (not previously registered as raft) must not
        mutate the raft context tracking sets through any lifecycle hook."""
        assert _is_raft_context(platform="tui", session_id="tui-1") is False

        _on_session_start(platform="tui", session_id="tui-1")
        _on_pre_llm_call(platform="tui", session_id="tui-1", turn_id="tui-turn-1")
        _on_session_end(platform="tui", session_id="tui-1")
        _on_session_finalize(platform="tui", session_id="tui-1")

        assert _RAFT_SESSION_IDS == set()
        assert _RAFT_TURN_IDS == set()
        assert _RAFT_PROMPT_TURN_IDS == set()
