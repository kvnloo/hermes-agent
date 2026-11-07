"""The TUI session picker must not list content-less session rows (#143659).

``session.list`` (the picker) and ``session.most_recent`` (auto-resume) both ride
``_listing_rows``. A TUI start writes a session row before any prompt exists, so a client
that launches ``hermes`` per tab (the Obsidian Hermes Console does) leaves one 0-message row
per abandoned tab; the picker showed them as unnamed entries and auto-resume could land on
one. The rows stay in the store — the listing just skips them.
"""

import pytest


@pytest.fixture
def db(tmp_path):
    from hermes_state import SessionDB

    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("sess_real", "tui")
    db.append_message("sess_real", "user", "a real conversation")
    db.create_session("sess_ghost", "tui")  # launch that never got a prompt
    yield db
    db.close()


def test_listing_rows_skip_content_less_sessions(db):
    from tui_gateway.methods_session import _listing_rows

    ids = [row["id"] for row in _listing_rows(db, 20)]
    assert ids == ["sess_real"]


def test_named_zero_message_cli_draft_stays_in_picker(db):
    """A named draft survives, but restart's untitled CLI placeholder does not."""
    from tui_gateway.methods_session import _listing_rows

    db.create_session("sess_gateway_ghost", "cli")
    db.create_session("sess_named_draft", "cli")
    db.set_session_title("sess_named_draft", "Saved before first message")

    ids = [row["id"] for row in _listing_rows(db, 20)]
    assert "sess_real" in ids
    assert "sess_named_draft" in ids
    assert "sess_gateway_ghost" not in ids
    assert "sess_ghost" not in ids
