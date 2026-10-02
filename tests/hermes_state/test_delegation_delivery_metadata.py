"""Delivery identity must agree with supported legacy display-metadata reads."""

import json
import sqlite3

import pytest

from hermes_state import SessionDB


@pytest.mark.parametrize("double_encoded", [False, True])
@pytest.mark.parametrize("rotated", [False, True])
@pytest.mark.parametrize("suppressed", [False, True])
def test_supported_metadata_encoding_keeps_delivery_identity(
    tmp_path, double_encoded, rotated, suppressed
):
    db = SessionDB(tmp_path / "state.db")
    try:
        db.create_session("origin", source="api_server")
        metadata = {
            "delegation_id": "unit",
            "delivery_notice": "task_failure:0" if suppressed else "",
        }
        if suppressed:
            metadata["presentation_suppressed"] = True
        original = db.append_delegation_delivery(
            "origin", "completed payload", metadata
        )
        if double_encoded:
            raw = db._conn.execute(
                "SELECT display_metadata FROM messages WHERE id = ?", (original,)
            ).fetchone()[0]
            db._conn.execute(
                "UPDATE messages SET display_metadata = ? WHERE id = ?",
                (json.dumps(raw), original),
            )
            db._conn.commit()
        # This is a supported legacy representation, readable through the public decoder.
        assert db.get_messages("origin")[0]["display_metadata"] == metadata
        target = "origin"
        if rotated:
            db.end_session("origin", "compression")
            db.create_session("tip", source="api_server", parent_session_id="origin")
            target = "tip"
        before = tuple(
            db._conn.execute(
                "SELECT id, content, display_metadata FROM messages ORDER BY id"
            ).fetchall()
        )
        repeated = db.append_delegation_delivery(target, "retry payload", metadata)
        assert repeated == original
        assert (
            tuple(
                db._conn.execute(
                    "SELECT id, content, display_metadata FROM messages ORDER BY id"
                ).fetchall()
            )
            == before
        )
        # A different notice on the same unit remains a distinct delivery.
        other = db.append_delegation_delivery(
            target, "different notice", {**metadata, "delivery_notice": "distinct"}
        )
        assert other != original
        assert db._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
        assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        db.close()


@pytest.mark.parametrize(
    ("raw", "refuses"),
    [
        ("{", True),
        (json.dumps("{"), False),
        ("[]", False),
        ("null", False),
        ("7", False),
        (json.dumps(json.dumps(json.dumps({"delegation_id": "unit"}))), False),
    ],
)
def test_unreadable_identity_preserves_existing_write_outcome(tmp_path, raw, refuses):
    db = SessionDB(tmp_path / "state.db")
    try:
        db.create_session("origin", source="api_server")
        metadata = {"delegation_id": "unit"}
        original = db.append_delegation_delivery(
            "origin", "completed payload", metadata
        )
        db._conn.execute(
            "UPDATE messages SET display_metadata = ? WHERE id = ?", (raw, original)
        )
        db._conn.commit()
        before = tuple(
            db._conn.execute(
                "SELECT id, content, display_metadata FROM messages ORDER BY id"
            ).fetchall()
        )
        if refuses:
            with pytest.raises(sqlite3.OperationalError, match="malformed JSON"):
                db.append_delegation_delivery("origin", "retry payload", metadata)
            assert (
                tuple(
                    db._conn.execute(
                        "SELECT id, content, display_metadata FROM messages ORDER BY id"
                    ).fetchall()
                )
                == before
            )
        else:
            # Preserve the existing outcome for shapes outside the readable object contract.
            assert (
                db.append_delegation_delivery("origin", "retry payload", metadata)
                != original
            )
            assert (
                tuple(
                    db._conn.execute(
                        "SELECT id, content, display_metadata FROM messages WHERE id = ?",
                        (original,),
                    ).fetchall()
                )
                == before
            )
            assert db._conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
        assert db._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        db.close()
