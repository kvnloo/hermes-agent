"""A corrupt state.db must not be reported as a missing session.

Regression for the 2026-08-31 incident: ``state.db`` corruption (rowid out of
order in ``sessions``, wrong entry count in ``idx_messages_session_id``) made
``resolve_session_id`` raise ``sqlite3.DatabaseError: database disk image is
malformed``. The Desktop showed "Couldn't open this session - session
unavailable" and the main process logged ``404: {"detail":"Session not
found"}`` — a session that existed was reported as absent, which sent the
diagnosis in entirely the wrong direction for a day.

A corrupt store is an unavailable store, not an empty one.
"""

import sqlite3

import pytest
from fastapi import HTTPException

from hermes_cli import web_server
from hermes_cli.web_routers import sessions as sessions_router


class _MalformedDB:
    """SessionDB stand-in that fails the way a corrupt file really fails."""

    def __init__(self):
        self.closed = False

    def resolve_session_id(self, session_id):
        raise sqlite3.DatabaseError("database disk image is malformed")

    def get_session(self, sid):  # pragma: no cover - never reached
        raise AssertionError("resolve_session_id should have raised first")

    def close(self):
        self.closed = True


@pytest.fixture
def malformed_db(monkeypatch):
    db = _MalformedDB()
    monkeypatch.setattr(
        web_server, "_open_session_db_for_profile", lambda profile, *, read_only: db
    )
    return db


@pytest.mark.asyncio
async def test_corrupt_db_is_not_reported_as_missing_session(malformed_db):
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.get_session_detail("20260830_180820_744f05")

    assert excinfo.value.status_code != 404, (
        "corruption reported as 'Session not found' - this is the bug"
    )
    assert excinfo.value.status_code == 503


@pytest.mark.asyncio
async def test_corrupt_db_detail_names_the_real_cause(malformed_db):
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.get_session_detail("20260830_180820_744f05")

    detail = str(excinfo.value.detail).lower()
    assert "corrupt" in detail or "malformed" in detail


@pytest.mark.asyncio
async def test_db_is_closed_even_when_corruption_raises(malformed_db):
    with pytest.raises(HTTPException):
        await sessions_router.get_session_detail("20260830_180820_744f05")

    assert malformed_db.closed, "connection leaked on the corruption path"


# ── The same lookup runs in four more handlers ──────────────────────────────
#
# delete is the dangerous one: an unresolvable id is treated as idempotent
# success ({"ok": True, "already_absent": True}), so a corrupt store made
# DELETE report that it had removed a session that is still on disk — and the
# Desktop drops the sidebar row on that answer.


@pytest.mark.asyncio
async def test_messages_endpoint_reports_corruption(malformed_db):
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.get_session_messages(
            "20260830_180820_744f05", None, None, 0, None, False
        )
    assert excinfo.value.status_code == 503


@pytest.mark.asyncio
async def test_delete_does_not_claim_success_on_a_corrupt_store(malformed_db):
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.delete_session_endpoint("20260830_180820_744f05")
    assert excinfo.value.status_code == 503


@pytest.mark.asyncio
async def test_rename_endpoint_reports_corruption(malformed_db):
    from hermes_cli.web_models import SessionRename

    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.rename_session_endpoint(
            "20260830_180820_744f05", SessionRename(title="neu")
        )
    assert excinfo.value.status_code == 503


@pytest.mark.asyncio
async def test_export_endpoint_reports_corruption(malformed_db):
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.export_session_endpoint("20260830_180820_744f05")
    assert excinfo.value.status_code == 503


# ── A genuinely absent session must still be a 404, not a 503 ──────────────


class _EmptyDB:
    def __init__(self):
        self.closed = False

    def resolve_session_id(self, session_id):
        return None

    def get_session(self, sid):
        return None

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_absent_session_is_still_404(monkeypatch):
    monkeypatch.setattr(
        web_server,
        "_open_session_db_for_profile",
        lambda profile, *, read_only: _EmptyDB(),
    )
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.get_session_detail("does_not_exist")
    assert excinfo.value.status_code == 404


# ── Unrelated DatabaseErrors must not be relabelled as corruption ──────────


class _OtherErrorDB(_EmptyDB):
    def resolve_session_id(self, session_id):
        raise sqlite3.DatabaseError("some unrelated database failure")


@pytest.mark.asyncio
async def test_non_corruption_database_error_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(
        web_server,
        "_open_session_db_for_profile",
        lambda profile, *, read_only: _OtherErrorDB(),
    )
    with pytest.raises(sqlite3.DatabaseError):
        await sessions_router.get_session_detail("20260830_180820_744f05")


# ── Post-resolve corruption in get_session_messages (ba7743b scope gap) ────
#
# _resolve_session_id only classifies a corrupt *sessions* index. get_messages
# reads the *messages* b-tree afterwards, and a partial corruption (sessions PK
# intact, messages b-tree damaged - the 2026-08-31 incident shape) sails past
# the resolve step and used to raise an unhandled sqlite3.DatabaseError out of
# asyncio.to_thread, rendering as a bare 500 with no repair path instead of the
# 503 "run `hermes doctor`" diagnostic the resolve step already emits.


class _MessagesOnlyMalformedDB:
    """Sessions PK intact, messages b-tree damaged.

    resolve_session_id succeeds (PK lookup), resolve_resume_session_id
    swallows the corruption and falls back to the id, and get_messages is the
    first uncaught raise - exactly the chain a real zeroed messages rootpage
    produces.
    """

    def __init__(self):
        self.closed = False

    def resolve_session_id(self, session_id):
        return session_id  # PK index intact -> resolve SUCCEEDS

    def resolve_resume_session_id(self, session_id):
        return session_id  # swallows corruption -> falls back unchanged

    def get_messages(self, session_id, **kwargs):
        raise sqlite3.DatabaseError("database disk image is malformed")

    def close(self):
        self.closed = True


@pytest.fixture
def messages_malformed_db(monkeypatch):
    db = _MessagesOnlyMalformedDB()
    monkeypatch.setattr(
        web_server, "_open_session_db_for_profile", lambda profile, *, read_only: db
    )
    return db


@pytest.mark.asyncio
async def test_messages_endpoint_reports_post_resolve_corruption(messages_malformed_db):
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.get_session_messages(
            "20260830_180820_744f05", None, None, 0, None, False
        )
    assert excinfo.value.status_code != 500, (
        "post-resolve corruption returned a bare 500 - this is the bug"
    )
    assert excinfo.value.status_code != 404
    assert excinfo.value.status_code == 503
    detail = str(excinfo.value.detail).lower()
    assert "corrupt" in detail or "malformed" in detail
    assert "hermes doctor" in detail


class _MessagesOtherErrorDB(_MessagesOnlyMalformedDB):
    def get_messages(self, session_id, **kwargs):
        raise sqlite3.DatabaseError("some unrelated messages read failure")


@pytest.mark.asyncio
async def test_post_resolve_non_corruption_database_error_not_swallowed(monkeypatch):
    monkeypatch.setattr(
        web_server,
        "_open_session_db_for_profile",
        lambda profile, *, read_only: _MessagesOtherErrorDB(),
    )
    with pytest.raises(sqlite3.DatabaseError):
        await sessions_router.get_session_messages(
            "20260830_180820_744f05", None, None, 0, None, False
        )


@pytest.mark.asyncio
async def test_absent_session_messages_still_404(monkeypatch):
    monkeypatch.setattr(
        web_server,
        "_open_session_db_for_profile",
        lambda profile, *, read_only: _EmptyDB(),
    )
    with pytest.raises(HTTPException) as excinfo:
        await sessions_router.get_session_messages(
            "does_not_exist", None, None, 0, None, False
        )
    assert excinfo.value.status_code == 404


# ── End-to-end through the real mounted router + a real corrupt SQLite file ─
#
# The mock tests above pin the classification branch; this pair reproduces the
# reported HTTP transition (500 -> 503) with a real state.db whose messages
# b-tree root page is zeroed while the sessions primary-key index stays intact
# - the partial-corruption shape from the 2026-08-31 incident.


def _build_healthy_store_with_messages() -> str:
    import uuid

    from hermes_state import SessionDB

    db = SessionDB()
    sid = db.create_session(session_id=str(uuid.uuid4()), source="test")
    for i in range(3):
        db.append_message(sid, role="user", content=f"hello world {i}")
    db.close()
    return sid


def _zero_messages_rootpage(db_path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        rootpage = conn.execute(
            "SELECT rootpage FROM sqlite_master WHERE type='table' AND name='messages'"
        ).fetchone()[0]
    finally:
        conn.close()
    with open(db_path, "r+b") as f:
        f.seek((rootpage - 1) * page_size)
        f.write(b"\x00" * page_size)


def test_messages_endpoint_real_corrupt_messages_btree_returns_503():
    from starlette.testclient import TestClient

    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app
    from hermes_state import _default_db_path

    sid = _build_healthy_store_with_messages()
    _zero_messages_rootpage(_default_db_path())

    client = TestClient(app, raise_server_exceptions=False)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    resp = client.get(f"/api/sessions/{sid}/messages")

    assert resp.status_code != 500, (
        "real post-resolve corruption returned a bare 500 - this is the bug"
    )
    assert resp.status_code == 503, resp.text
    detail = str(resp.json().get("detail", "")).lower()
    assert "corrupt" in detail or "malformed" in detail
    assert "hermes doctor" in detail


def test_messages_endpoint_real_healthy_store_still_returns_200():
    from starlette.testclient import TestClient

    from hermes_cli.web_server import _SESSION_HEADER_NAME, _SESSION_TOKEN, app

    sid = _build_healthy_store_with_messages()

    client = TestClient(app, raise_server_exceptions=False)
    client.headers[_SESSION_HEADER_NAME] = _SESSION_TOKEN
    resp = client.get(f"/api/sessions/{sid}/messages")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["session_id"] == sid
    assert len(body["messages"]) == 3
