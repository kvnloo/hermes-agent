"""Deferred soft-release for agents evicted mid-turn.

_drop_turn_slot (the /stop, /new and eviction tail) clears the running slot BEFORE
_evict_cached_agent runs, so the "never tear down a mid-turn agent" guard can no longer
fire for the just-interrupted turn: release_clients() and the transcript wipe ran on a
daemon thread while the worker was still unwinding (use-after-release). The evicted
agent's soft release is now deferred until its own turn finalizer drains it.
"""

import threading
import types


class _FakeAgent:
    def __init__(self):
        self.release_calls = 0
        self._session_messages = [{"role": "user", "content": "hi"}]
        self._db_flush_scan_prefix = [{"role": "user", "content": "hi"}]

    def release_clients(self):
        self.release_calls += 1


def _make_runner():
    from gateway.run import GatewayRunner

    runner = GatewayRunner.__new__(GatewayRunner)
    runner._agent_cache = {}
    runner._agent_cache_lock = threading.Lock()
    runner._persist_active_agents = lambda: None
    runner._release_calls = []  # (target, args, name, session_key) per _spawn_release_thread

    def _spawn(target, args, name, *, inline_fallback, session_key=None):
        runner._release_calls.append((target, args, name, session_key))

    runner._spawn_release_thread = _spawn
    return runner


def _running_turn(runner, key, worker_generation=7):
    """Promote a fake agent into the running slot and the cache, mid-turn."""
    from gateway.session_state import SessionState

    state = SessionState()
    agent = _FakeAgent()
    state.turn.agent = agent
    state.turn.ctx = types.SimpleNamespace(run_generation=worker_generation)
    # Post-bump value, as _interrupt_running_turn leaves it before _drop_turn_slot.
    state.persistent.run_generation = worker_generation + 1
    runner._sessions_map()[key] = state
    runner._agent_cache[key] = (agent, "sig")
    return agent


def test_drop_turn_slot_defers_soft_release_until_worker_finishes():
    runner = _make_runner()
    key = "agent:test:1"
    agent = _running_turn(runner, key, worker_generation=7)
    # Post-bump generation, exactly as _interrupt_and_clear_session passes it.
    runner._drop_turn_slot(key, run_generation=8)
    # Cache entry is popped: the next message still rebuilds fresh (#44212).
    assert key not in runner._agent_cache
    # The worker may still be unwinding: no soft release may have run yet.
    assert runner._release_calls == []
    # The worker's own finalizer drains the deferred release exactly once.
    runner._drain_deferred_agent_release(key, 7)
    assert len(runner._release_calls) == 1
    assert runner._release_calls[0][1][0] is agent
    runner._drain_deferred_agent_release(key, 7)
    assert len(runner._release_calls) == 1


def test_drain_ignores_other_generations():
    runner = _make_runner()
    key = "agent:test:2"
    _running_turn(runner, key, worker_generation=7)
    runner._drop_turn_slot(key, run_generation=8)
    # A different worker's finalizer must not release this agent.
    runner._drain_deferred_agent_release(key, 9)
    assert runner._release_calls == []
    # The owning worker's finalizer releases it.
    runner._drain_deferred_agent_release(key, 7)
    assert len(runner._release_calls) == 1


def test_idle_evict_still_releases_immediately():
    """No running turn: eviction keeps its existing prompt-release behavior."""
    from gateway.session_state import SessionState

    runner = _make_runner()
    key = "agent:test:3"
    agent = _FakeAgent()
    runner._sessions_map()[key] = SessionState()
    runner._agent_cache[key] = (agent, "sig")
    runner._drop_turn_slot(key)
    assert key not in runner._agent_cache
    assert len(runner._release_calls) == 1
    assert runner._release_calls[0][1][0] is agent
