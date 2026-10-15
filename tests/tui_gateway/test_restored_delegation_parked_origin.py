"""Owner-head regression: parked origin must not monopolize restored delegation.

Original incident: @predatorheard-byte (#138343). Existing owner fix: @KoNit-K
(#138348). Reviewer @Schubox84 identified standalone stdio compatibility.
This companion tests *routing after resume*, without owning their implementation.
"""

from types import SimpleNamespace

import pytest
from tui_gateway import server


def _session(key, transport, *, finalized=False):
    return {"session_key": key, "transport": transport, "_finalized": finalized}


def _restored(*, owner="ui-old", key="shared", restored=True):
    return {"type": "async_delegation", "restored": restored,
            "origin_ui_session_id": owner, "session_key": key, "delegation_id": "d-original"}


@pytest.fixture
def sessions(monkeypatch):
    # The original owner may remain registered but parked after WS disconnect,
    # while a new tab resumes the same persisted session key.
    old = _session("shared", server._detached_ws_transport)
    new = _session("shared", SimpleNamespace(write=lambda _frame: True, close=lambda: None))
    registry = {"ui-old": old, "ui-new": new}
    with server._sessions_lock:
        saved = dict(server._sessions)
        server._sessions.clear()
        server._sessions.update(registry)
    monkeypatch.setattr(server, "_notif_resolve_event_key", lambda key, session=None: key)
    try:
        yield old, new
    finally:
        with server._sessions_lock:
            server._sessions.clear()
            server._sessions.update(saved)


def test_parked_origin_does_not_block_restored_completion_from_live_resumer(sessions):
    old, new = sessions
    evt = _restored()
    assert server._session_owns_notification_event("ui-old", old, evt) is False
    assert server._session_owns_notification_event("ui-new", new, evt) is True
    assert server._notification_event_belongs_elsewhere("ui-new", new, evt) is False


def test_active_origin_still_owns_restored_completion(sessions):
    old, new = sessions
    old["transport"] = SimpleNamespace(write=lambda _frame: True, close=lambda: None)
    evt = _restored()
    assert server._session_owns_notification_event("ui-old", old, evt) is True
    assert server._notification_event_belongs_elsewhere("ui-new", new, evt) is True


def test_unrestored_origin_priority_unchanged(sessions):
    old, new = sessions
    # Pre-existing ownership behavior for non-restored process-local events.
    assert server._notification_event_belongs_elsewhere(
        "ui-new", new, _restored(restored=False)) is True


def test_wrong_resumer_never_claims_parked_completion(sessions):
    old, new = sessions
    new["session_key"] = "unrelated"
    evt = _restored()
    assert server._session_owns_notification_event("ui-new", new, evt) is False


def test_finalized_origin_allows_live_resumer(sessions):
    old, new = sessions
    old["_finalized"] = True
    evt = _restored()
    assert server._notification_event_belongs_elsewhere("ui-new", new, evt) is False
