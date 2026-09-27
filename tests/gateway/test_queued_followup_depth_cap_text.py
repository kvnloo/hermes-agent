"""The depth-cap branch must park text-only follow-ups, not silently drop them.

When the follow-up recursion hits _MAX_INTERRUPT_DEPTH, _run_agent_queued_followup
parks the follow-up instead of recursing. Its text-only fallback —
``elif adapter and hasattr(adapter, 'queue_message')`` — is dead: no adapter in the
tree defines ``queue_message``. A text-only follow-up (a leftover /steer from
``result["pending_steer"]``, or an interrupt text with no queued event) vanished
while the log claimed "queueing message instead of recursing".
"""

import types

import pytest


def _make_runner(adapter):
    from gateway.run import GatewayRunner

    runner = GatewayRunner.__new__(GatewayRunner)
    runner._delivery_adapter_for = lambda source: adapter
    return runner


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


def _adapter():
    return types.SimpleNamespace(_pending_messages={}, _active_sessions={})


@pytest.mark.asyncio
async def test_depth_cap_parks_text_only_followup():
    """A leftover /steer at the depth cap must land in the pending slot."""
    adapter = _adapter()
    runner = _make_runner(adapter)
    key = "agent:main:qtext"

    await runner._run_agent_queued_followup(
        _cap_ctx(key), adapter, "also handle the refund", None, "resp",
        {"interrupted": False}, None,
    )
    parked = adapter._pending_messages.get(key)
    assert parked is not None
    assert parked.text == "also handle the refund"


@pytest.mark.asyncio
async def test_depth_cap_still_parks_event():
    """The event path keeps working: pinned so the text fix can't regress it."""
    from gateway.platforms.event import MessageEvent

    adapter = _adapter()
    runner = _make_runner(adapter)
    key = "agent:main:qevt"
    event = MessageEvent(text="m4")

    await runner._run_agent_queued_followup(
        _cap_ctx(key), adapter, "m4", event, "resp", {"interrupted": False}, None,
    )
    assert adapter._pending_messages[key] is event
