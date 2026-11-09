"""A completed fallback turn remains in the running map until outer settlement."""
from types import SimpleNamespace
from unittest.mock import Mock
from tests.gateway.test_agent_cache import _make_runner
from tests.gateway.test_signature_change_releases_memory import ResourceAgent, no_source_updater


def test_successful_fallback_keeps_release_owner_until_turn_settles():
    runner = _make_runner()
    key = 'agent:main:telegram:dm:fallback-release'
    old = ResourceAgent()
    old.model = 'fallback'
    old._provider_fallback_active = True
    state = runner._session_state(key)
    state.turn.agent = old
    runner._agent_cache[key] = (old, 'signature', 0, 'session')
    runner._persist_active_agents = Mock()
    runner._spawn_release_thread = lambda target, args, *a, **kw: target(*args)
    try:
        runner._run_agent_evict_on_fallback(SimpleNamespace(session_key=key, agent_holder=[old],
                                                          result_holder=[{'failed':False}]))
        assert key not in runner._agent_cache
        assert state.turn.retired_agents == [old], 'fallback dropped cache ownership without arranging release'
        assert old.releases == 0  # never release resources before turn settlement
        runner._release_running_agent_state(key)
        assert old.releases == 1
        assert not old.provider.writer.is_alive()
    finally:
        old.cleanup()


def test_stale_fallback_does_not_retire_newer_turn():
    """An older successful fallback must not evict a replacement turn's agent."""
    runner = _make_runner()
    key = "agent:main:telegram:dm:stale-fallback"
    old = SimpleNamespace(model="fallback", _provider_fallback_active=True)
    successor = ResourceAgent()
    state = runner._session_state(key)
    state.persistent.run_generation = 2
    state.turn.agent = successor
    runner._agent_cache[key] = (successor, "current", 0, "session")
    runner._persist_active_agents = Mock()
    runner._spawn_release_thread = lambda target, args, *a, **kw: target(*args)
    try:
        assert not runner._is_session_run_current(key, 1)
        runner._run_agent_evict_on_fallback(SimpleNamespace(
            session_key=key, run_generation=1, agent_holder=[old],
            result_holder=[{"failed": False}],
        ))
        runner._release_running_agent_state(key, run_generation=2)
        assert runner._agent_cache[key][0] is successor
        assert successor.releases == 0
        assert successor.provider.writer.is_alive()
    finally:
        successor.cleanup()
