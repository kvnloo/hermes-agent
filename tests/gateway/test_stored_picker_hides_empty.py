"""Canonical TUI stored-history listing excludes launch ghosts (#143659).

The legacy TUI and CLI list helpers are separate from the canonical gateway's
stored history feed. Its zero-message placeholders must not enter the picker,
while an explicitly titled draft remains selectable.
"""

from types import SimpleNamespace

from gateway import session_listing
from hermes_state import SessionDB


def test_canonical_stored_picker_excludes_untitled_ghost(tmp_path, monkeypatch):
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        db.create_session("sess_real", "tui")
        db.append_message("sess_real", "user", "hello")
        db.create_session("sess_ghost", "tui")
        db.create_session("sess_named", "tui")
        db.set_session_title("sess_named", "Draft worth keeping")

        actor = SimpleNamespace(
            profile_id="test-profile",
            transport_id="native",
            capabilities={"session:read", "session:create"},
            subject="human",
        )
        authority = SimpleNamespace(
            profile_id=actor.profile_id,
            db=db,
            _native_legacy_transports={"native": actor},
            sessions={},
        )
        # Isolate listing eligibility from migration and principal authorization.
        monkeypatch.setattr(session_listing, "validate_legacy_row", lambda *args, **kwargs: None)
        monkeypatch.setattr(session_listing, "authorize_history", lambda *args, **kwargs: True)

        result = session_listing.stored_picker_sessions(authority, actor, limit=20)
        assert result["scope"] == "stored"
        assert {row["id"] for row in result["sessions"]} == {"sess_real", "sess_named"}
    finally:
        db.close()
