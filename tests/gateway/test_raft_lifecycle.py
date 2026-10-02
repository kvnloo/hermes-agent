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

    def test_completed_turns_do_not_accumulate_per_session_entries(self):
        """The reverse index must not move the leak into a long-lived session."""
        for index in range(4):
            turn_id = f"turn-{index}"
            self._drive_session_turn("live-session", turn_id)
            _on_session_end(platform="raft", session_id="live-session", turn_id=turn_id, completed=True)
            assert _RAFT_SESSION_IDS == {"live-session"}
            assert not _RAFT_TURN_IDS and not _RAFT_PROMPT_TURN_IDS
            assert not getattr(raft_mod, "_RAFT_SESSION_TURNS", {}).get("live-session")


def test_loaded_plugin_lifecycle_finalizes_only_selected_session(monkeypatch, tmp_path):
    """Real manifest loader, registration and dispatch; no Raft HTTP/CLI connection."""
    import importlib
    from pathlib import Path
    import weakref

    from hermes_cli import lifecycle, plugins
    from hermes_cli.plugins_manifest import parse_manifest_file

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    plugin_dir = Path(raft_mod.__file__).resolve().parent
    manifest = parse_manifest_file(plugin_dir / "plugin.yaml", plugin_dir, "bundled", "platforms")
    assert manifest is not None
    manager = plugins.PluginManager(scope_key=str(tmp_path))
    try:
        manager._load_plugin(manifest)
        loaded = manager._plugins[manifest.key]
        assert loaded.enabled and not loaded.error
        manager._discovered = True  # This test explicitly loaded its one real manifest.
        monkeypatch.setattr(plugins, "get_plugin_manager", lambda: manager)
        module = importlib.import_module(loaded.module.register.__module__)
        assert Path(module.__file__).resolve() == Path(raft_mod.__file__).resolve()
        adapter = module.RaftAdapter(PlatformConfig(enabled=True, extra={
            "bridge_token": "fixture-token", "runtime_session": "default", "port": 0,
        }))
        monkeypatch.setattr(module, "_ACTIVE_ADAPTERS", weakref.WeakSet([adapter]))
        for session_id, turn_id in (("left-session", "left-turn"), ("right-session", "right-turn")):
            lifecycle.invoke_hook("on_session_start", platform="raft", session_id=session_id)
            lifecycle.invoke_hook("pre_llm_call", platform="raft", session_id=session_id, turn_id=turn_id)
        assert module._RAFT_TURN_IDS == {"left-turn", "right-turn"}
        lifecycle.invoke_hook("on_session_end", platform="raft", session_id="left-session", interrupted=True)
        lifecycle.finalize_session(platform="raft", session_id="left-session", reason="fixture-teardown")
        assert module._RAFT_TURN_IDS == {"right-turn"}
        assert module._RAFT_PROMPT_TURN_IDS == {"right-turn"}
        assert module._RAFT_SESSION_IDS == {"right-session"}
        events = adapter._activity_queue.drain()["events"]
        assert [(event["sessionId"], event["hookEventName"]) for event in events] == [
            ("left-session", "SessionStart"), ("left-session", "UserPromptSubmit"),
            ("right-session", "SessionStart"), ("right-session", "UserPromptSubmit"),
            ("left-session", "Stop"), ("left-session", "SessionEnd"),
        ]
        lifecycle.finalize_session(platform="raft", session_id="right-session", reason="fixture-teardown")
        assert not module._RAFT_TURN_IDS and not module._RAFT_PROMPT_TURN_IDS
        assert not module._RAFT_SESSION_IDS and not module._RAFT_SESSION_TURNS
    finally:
        manager.unload()
