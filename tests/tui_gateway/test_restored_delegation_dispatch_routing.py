"""Regression for #138348: restored completions follow an attached resumer.

Reported incident: @predatorheard-byte (#138343); existing fix: @KoNit-K
(#138348). @Schubox84 reported the separate standalone-stdio risk.
This test-only companion covers the *actual notification dispatch admission*.
"""

from queue import Queue
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from tui_gateway import server


def _event(*, key="shared", restored=True):
    return {
        "type": "async_delegation", "restored": restored,
        "origin_ui_session_id": "ui-old", "session_key": key,
        "delegation_id": "deleg-wave11", "results": [],
    }


def _session(key, transport):
    return {"session_key": key, "transport": transport, "_finalized": False}


@pytest.fixture
def route(monkeypatch):
    from tools import process_registry_notifications as notifications
    from gateway import warning_notifications

    old = _session("shared", server._detached_ws_transport)
    new = _session("shared", SimpleNamespace(write=lambda _frame: True, close=lambda: None))
    with server._sessions_lock:
        saved = dict(server._sessions)
        server._sessions.clear()
        server._sessions.update({"ui-old": old, "ui-new": new})
    monkeypatch.setattr(server, "_notif_resolve_event_key", lambda key, session=None: key)
    monkeypatch.setattr(server, "_notif_claim_turn", lambda _session: True)
    dispatched = Mock()
    monkeypatch.setattr(server, "_notif_dispatch_event", dispatched)
    monkeypatch.setattr(server, "_emit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(notifications, "async_delegation_display_text", lambda _evt: "done")
    monkeypatch.setattr(warning_notifications, "render_notification", lambda cb, **_kwargs: cb())
    queue = Queue()
    registry = SimpleNamespace(completion_queue=queue)

    def poll(sid, evt):
        session = old if sid == "ui-old" else new
        return server._notif_handle_event(
            sid, session, evt, set(), registry, lambda _evt: "done", None,
        )

    try:
        yield old, new, queue, dispatched, poll
    finally:
        with server._sessions_lock:
            server._sessions.clear()
            server._sessions.update(saved)


def test_parked_origin_no_longer_requeues_instead_of_dispatching(route):
    _old, _new, queue, dispatched, poll = route
    assert poll("ui-new", _event()) is True
    assert queue.empty(), "a live resumer must not spin a completion in the queue"
    dispatched.assert_called_once()
    assert dispatched.call_args.args[0] == "ui-new"


def test_compression_rotated_resumer_claims_parked_origin_completion(route, monkeypatch):
    old, new, queue, dispatched, poll = route
    old["session_key"], new["session_key"] = "parent", "child"
    monkeypatch.setattr(server, "_notif_resolve_event_key", lambda key, session=None:
                        "child" if key == "parent" else key)
    assert poll("ui-new", _event(key="parent")) is True
    assert queue.empty()
    dispatched.assert_called_once()


def test_live_original_client_keeps_priority_over_other_tab(route):
    old, _new, queue, dispatched, poll = route
    old["transport"] = SimpleNamespace(write=lambda _frame: True, close=lambda: None)
    assert poll("ui-new", _event()) is True
    assert queue.qsize() == 1
    dispatched.assert_not_called()


def test_requeued_event_delivers_once_after_original_client_detaches(route):
    old, _new, queue, dispatched, poll = route
    old["transport"] = SimpleNamespace(write=lambda _frame: True, close=lambda: None)
    assert poll("ui-new", _event()) is True
    old["transport"] = server._detached_ws_transport
    assert poll("ui-new", queue.get_nowait()) is True
    assert queue.empty()
    dispatched.assert_called_once()


def test_nonrestored_event_keeps_original_client_priority(route):
    _old, _new, queue, dispatched, poll = route
    assert poll("ui-new", _event(restored=False)) is True
    assert queue.qsize() == 1
    dispatched.assert_not_called()
