"""Depth-cap parking in _run_agent_queued_followup must not lose the staged message.

_run_agent_drain_pending pops each follow-up from the adapter's pending slot and stages
the next overflow head into the slot via _promote_queued_event. When the 4th chained
follow-up hits _MAX_INTERRUPT_DEPTH, the cap branch parked its event with
merge_pending_message_event — which REPLACES text-on-text, silently dropping the staged
message. Five rapid messages during one turn was enough to lose one.
"""

import types

import pytest


def _make_runner():
    from gateway.run import GatewayRunner

    runner = GatewayRunner.__new__(GatewayRunner)
    runner._delivery_adapter_for = lambda source: runner._test_adapter
    return runner


def _msg(text):
    from gateway.platforms.event import MessageEvent

    return MessageEvent(text=text)


def _adapter():
    adapter = types.SimpleNamespace(_pending_messages={}, _active_sessions={})
    adapter.get_pending_message = lambda sk: adapter._pending_messages.pop(sk, None)
    return adapter


def _drain(runner, adapter, key):
    """One post-turn drain cycle through the real helpers: pop the slot, stage next."""
    from gateway.run import _dequeue_pending_event

    return runner._promote_queued_event(key, adapter, _dequeue_pending_event(adapter, key))


def _cap_ctx(key):
    return types.SimpleNamespace(
        source=types.SimpleNamespace(),
        session_id="s",
        session_key=key,
        run_generation=7,
        _interrupt_depth=3,  # == _MAX_INTERRUPT_DEPTH: the cap branch
        history=[],
        _status_thread_metadata=None,
        result_holder=[{"interrupted": False}],
    )


@pytest.mark.asyncio
async def test_depth_cap_parking_preserves_staged_message():
    from gateway.session_state import SessionState

    runner = _make_runner()
    key = "agent:main:qtest"
    adapter = _adapter()
    runner._test_adapter = adapter
    state = SessionState()
    runner._sessions_map()[key] = state

    # 5 rapid messages during T0: m1 running, m2 in the slot, m3..m5 in overflow.
    m2, m3, m4, m5 = (_msg(f"m{i}") for i in range(2, 6))
    adapter._pending_messages[key] = m2
    state.conversation.queued_events.extend([m3, m4, m5])

    # T0/T1/T2 post-turn drains: each pops the slot head and stages the next.
    assert _drain(runner, adapter, key) is m2
    assert adapter._pending_messages[key] is m3
    assert _drain(runner, adapter, key) is m3
    assert adapter._pending_messages[key] is m4
    assert _drain(runner, adapter, key) is m4
    assert adapter._pending_messages[key] is m5  # staged for the next recursion

    # The 4th chained follow-up hits the depth cap while parking m4.
    await runner._run_agent_queued_followup(
        _cap_ctx(key), adapter, "m4", m4, "resp", {"interrupted": False}, None
    )
    # m4 parked in the slot; the staged m5 is back at the overflow front: FIFO intact.
    assert adapter._pending_messages[key] is m4
    assert list(state.conversation.queued_events) == [m5]


def test_park_with_empty_slot_needs_no_unstage():
    """pending_event that arrived via overflow-pop (slot was empty): plain park."""
    from gateway.session_state import SessionState

    runner = _make_runner()
    key = "agent:main:qtest2"
    adapter = _adapter()
    state = SessionState()
    runner._sessions_map()[key] = state
    m4 = _msg("m4")

    runner._park_capped_followup(adapter, key, m4)
    assert adapter._pending_messages[key] is m4
    assert list(state.conversation.queued_events) == []
