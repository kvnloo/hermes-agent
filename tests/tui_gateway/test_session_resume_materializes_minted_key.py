"""Minted session key recovery (#96793) without empty reconnect rows (#150338).

#96793 (original fix by ruangraung) made an unpersisted key resumable across a
gateway restart. Reporter kosmo888 showed that reattaching several abandoned
keys then left permanent zero-message Untitled rows. Keep recovery in memory
until the first prompt; other stored-key and fail-closed behaviors still apply.
"""

from __future__ import annotations

import pytest

from hermes_state import SessionDB
from tui_gateway import server

MINTED_KEY = "20260828_053121_3427a9"  # the morning's lost session shape
EXISTING_KEY = "20260827_224618_956bf8"


@pytest.fixture()
def real_db(monkeypatch, tmp_path):
    """Real SessionDB behind ``_get_db``, with the heavy resume machinery off."""
    db = SessionDB(db_path=tmp_path / "state.db")
    monkeypatch.setattr(server, "_get_db", lambda: db)
    monkeypatch.setattr(server, "_resolve_model", lambda: "test-model")
    monkeypatch.setattr(server, "_enable_gateway_prompts", lambda: None)
    monkeypatch.setattr(server, "_find_live_session_by_key", lambda _key, _home=None: None)
    monkeypatch.setattr(server, "_schedule_agent_build", lambda *a, **k: None)
    monkeypatch.setattr(server, "_schedule_session_cap_enforcement", lambda *a, **k: None)
    monkeypatch.setattr(server, "_maybe_schedule_auto_continue", lambda *a, **k: None)
    monkeypatch.setattr(server, "_default_session_cwd", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(server, "_profile_configured_cwd", lambda _home: str(tmp_path))
    monkeypatch.setattr(server, "_child_run_active", lambda _key, _home=None: False)
    known = set(server._sessions)
    yield db
    with server._sessions_lock:
        for sid in [s for s in server._sessions if s not in known]:
            server._sessions.pop(sid, None)
    db.close()


def _resume(**params):
    return server.handle_request({"id": "1", "method": "session.resume", "params": params})


def _assert_resumed_ok(resp, target):
    assert "error" not in resp, resp
    assert resp["result"]["resumed"] == target
    assert resp["result"]["session_id"], "a live runtime must be registered"


def test_resume_defers_minted_draft_until_first_prompt(real_db):
    """Crash recovery succeeds without a row until the first-prompt write hook."""
    resp = _resume(session_id=MINTED_KEY)

    _assert_resumed_ok(resp, MINTED_KEY)
    assert real_db.get_session(MINTED_KEY) is None
    live = server._sessions[resp["result"]["session_id"]]
    assert live["session_key"] == MINTED_KEY
    assert live["history"] == []
    assert server._ensure_session_db_row(live) is not False
    row = real_db.get_session(MINTED_KEY)
    assert row is not None
    assert row["source"] == "tui"


def test_reconnect_batch_keeps_unspoken_drafts_unpersisted(real_db):
    """A reconnect replay of three abandoned gui keys must not add Untitled rows."""
    keys = [MINTED_KEY, "20261107_051206_669822", "20261107_051240_9543e2"]
    responses = [_resume(session_id=key, source="gui") for key in keys]
    for key, resp in zip(keys, responses):
        _assert_resumed_ok(resp, key)
        assert server._sessions[resp["result"]["session_id"]]["session_key"] == key
        assert real_db.get_session(key) is None
    assert real_db.list_sessions_rich(source=None) == []
    repeated = _resume(session_id=keys[0], source="gui")
    _assert_resumed_ok(repeated, keys[0])
    assert repeated["result"]["session_id"] == responses[0]["result"]["session_id"]
    assert real_db.list_sessions_rich(source=None) == []


def test_resume_existing_row_unaffected(real_db):
    """A persisted session resumes normally and its row is not duplicated."""
    real_db.create_session(EXISTING_KEY, source="tui", model="test-model")
    real_db.append_message(EXISTING_KEY, "user", "hello")

    resp = _resume(session_id=EXISTING_KEY)

    _assert_resumed_ok(resp, EXISTING_KEY)
    # message_count stays 1 — a second create would have been an INSERT-OR-IGNORE
    # no-op, but the row must remain the same single conversation.
    assert real_db.get_session(EXISTING_KEY)["message_count"] == 1


def test_resume_garbage_id_still_4007(real_db):
    """Non-key garbage stays fail-closed: same error, no write."""
    resp = _resume(session_id="not-a-session")

    assert resp["error"]["code"] == 4007
    # nothing materialized for arbitrary strings
    assert len(real_db.list_sessions_rich(source="tui")) == 0


def test_resume_8hex_runtime_id_still_4007(real_db):
    """8-hex runtime session ids (``uuid4().hex[:8]``) are NOT stored keys."""
    resp = _resume(session_id="5a81f231")

    assert resp["error"]["code"] == 4007
    assert len(real_db.list_sessions_rich(source="tui")) == 0


def test_resume_lazy_watch_missing_key_still_4007(real_db):
    """Lazy subagent watch windows must not mint phantom rows for dead children."""
    resp = _resume(session_id=MINTED_KEY, lazy=True)

    assert resp["error"]["code"] == 4007
    assert real_db.get_session(MINTED_KEY) is None


def test_resume_minted_key_claimed_by_other_profile_fails_closed(real_db):
    """A key claimed by a live session under ANOTHER profile must not mint here.

    Mirrors test_resume_live_lazy_session's unscoped-resume fail-closed rule
    (#93296): the materialize gate must not turn a cross-profile leak into a
    phantom launch-store row. The key looks server-minted, but a live record
    owns it — routing guesses are forbidden.
    """
    record = {
        "history": [],
        "last_active": 0.0,
        "pending_title": "Bot Chat",
        "pending_hidden": True,
        "profile_home": "/tmp/other-profile",
        "running": False,
        "session_key": MINTED_KEY,
        "source": "desktop",
    }
    server._sessions["live-other-profile"] = record
    try:
        resp = _resume(session_id=MINTED_KEY)
        assert resp["error"]["code"] == 4007
        assert real_db.get_session(MINTED_KEY) is None
    finally:
        with server._sessions_lock:
            server._sessions.pop("live-other-profile", None)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("20260828_053121_3427a9", True),
        ("20260827_224618_956bf8", True),
        ("5a81f231", False),  # 8-hex runtime sid
        ("fcd97d0c", False),  # 8-hex runtime sid
        ("not-a-session", False),
        ("", False),
        ("20260828_053121_3427", False),  # too-short hex tail
        ("20260828_053121_3427a9ZZ", False),  # trailing garbage
        ("Bot Chat", False),  # titles are not keys
    ],
)
def test_is_server_minted_key_shape(value, expected):
    assert server._is_server_minted_key(value) is expected