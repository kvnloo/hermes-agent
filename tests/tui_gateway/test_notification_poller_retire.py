"""Retiring a session must stop its notification poller before teardown (#154716)."""

import threading

from tui_gateway import server


def test_pop_signals_poller_before_finalization(monkeypatch, tmp_path):
    """A reaped session has no poller even if its slow finalizer has not run."""
    sid = "retire-before-teardown"
    stop = threading.Event()
    session = {
        "profile_home": str(tmp_path),
        "transport": server._detached_ws_transport,
        "last_active": 0.0,
        "running": False,
        "_finalized": False,
        "_notif_stop": stop,
    }
    monkeypatch.setattr(server, "_sessions", {sid: session})
    monkeypatch.setattr(server, "_closed_session_activity", {})

    # Detached sessions stay registered (and their poller stays alive) until reaped.
    assert not stop.is_set()
    assert server._sessions[sid] is session

    popped = server._pop_session_by_id(sid)

    assert popped is session
    assert sid not in server._sessions
    assert session["_closing"] and not session["_finalized"]
    assert stop.is_set()
