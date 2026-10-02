"""Post-resolution read diagnostics from downstream #28, on the current route."""

import sqlite3

import pytest
from fastapi import HTTPException

from hermes_cli.web_routers import sessions


class ReadDB:
    def __init__(self, *, error=None, stage="messages", absent=False):
        self.error = error
        self.stage = stage
        self.absent = absent
        self.closed = False

    def resolve_session_id(self, session_id):
        return None if self.absent else session_id

    def resolve_resume_session_id(self, session_id):
        if self.stage == "resume" and self.error:
            raise self.error
        return session_id

    def get_messages(self, session_id, **kwargs):
        if self.error:
            raise self.error
        return [{"role": "user", "content": "preserved"}]

    def close(self):
        self.closed = True


@pytest.fixture
def read_messages(monkeypatch, tmp_path):
    def configure(db):
        monkeypatch.setattr(
            sessions, "_open_session_db_for_profile", lambda *a, **k: db
        )
        monkeypatch.setattr(
            sessions, "_project_for_display", lambda messages, **k: messages
        )
        monkeypatch.setattr(sessions, "_history_profile_home", lambda profile: tmp_path)
        monkeypatch.setattr(sessions, "_serving_profile", lambda profile: "default")
        return sessions.get_session_messages(
            "session-fixture",
            profile="default",
            limit=None,
            offset=0,
            order=None,
            include_compacted=False,
            inline_images=False,
        )

    return configure


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["resume", "messages"])
@pytest.mark.parametrize(
    "message",
    ["database disk image is malformed", "malformed database schema (messages)"],
)
async def test_postresolve_corruption_has_actionable_diagnostic_and_closes(
    read_messages, stage, message
):
    db = ReadDB(error=sqlite3.DatabaseError(message), stage=stage)
    with pytest.raises(HTTPException) as caught:
        await read_messages(db)
    assert caught.value.status_code == 503
    assert "corrupt" in caught.value.detail.lower()
    assert "hermes doctor" in caught.value.detail
    assert db.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    ["healthy", "absent", "other-db-error", "unrecognized-db-error", "http-error"],
)
async def test_postresolve_error_mapping_preserves_neighbor_contracts(
    read_messages, case
):
    error = {
        "other-db-error": sqlite3.DatabaseError("unrelated database failure"),
        "unrecognized-db-error": sqlite3.DatabaseError("file is not a database"),
        "http-error": HTTPException(status_code=409, detail="existing HTTP failure"),
    }.get(case)
    db = ReadDB(error=error, absent=case == "absent")
    if error is not None:
        with pytest.raises(type(error)) as caught:
            await read_messages(db)
        assert caught.value is error
    elif case == "absent":
        with pytest.raises(HTTPException) as caught:
            await read_messages(db)
        assert caught.value.status_code == 404
    else:
        result = await read_messages(db)
        assert result["messages"] == [{"role": "user", "content": "preserved"}]
        assert result["pagination"]["returned"] == 1
    assert db.closed
