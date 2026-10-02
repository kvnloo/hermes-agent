"""Repair-ledger read contract retained from downstream #70 / upstream #112039."""

import json
import sqlite3

import pytest

import hermes_state_repair as repair
from hermes_cli.sqlite_safe_read import connect_tracked


@pytest.fixture(params=[False, True], ids=["offline", "live-connection"])
def ledger_db(tmp_path, request):
    db = tmp_path / "state.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (content TEXT)")
    conn.execute("INSERT INTO messages VALUES ('preserved')")
    conn.commit()
    conn.close()
    fingerprint = repair._db_fingerprint(db)
    assert fingerprint is not None
    conn = connect_tracked(db) if request.param else None
    try:
        assert (repair._db_fingerprint(db) is None) is request.param
        yield db, fingerprint
    finally:
        if conn is not None:
            conn.close()


@pytest.mark.parametrize("bad", ["three", [], None, {}, float("inf"), float("nan")])
def test_invalid_attempt_count_recovers_without_resetting_budget(ledger_db, bad):
    db, fingerprint = ledger_db
    ledger = repair._repair_ledger_path(db)
    payload = json.dumps({"fingerprint": fingerprint, "failed_attempts": bad})
    ledger.write_text(payload, encoding="utf-8")

    assert repair._persistent_repair_attempts_exhausted(db) is False
    assert ledger.read_text(encoding="utf-8") == payload

    for recorded in range(1, repair._MAX_PERSISTENT_REPAIR_ATTEMPTS + 1):
        repair._record_repair_outcome(db, repaired=False)
        recovered = json.loads(ledger.read_text(encoding="utf-8"))
        assert recovered["fingerprint"] == fingerprint
        assert recovered["failed_attempts"] == recorded
        assert repair._persistent_repair_attempts_exhausted(db) is (
            recorded >= repair._MAX_PERSISTENT_REPAIR_ATTEMPTS
        )

    conn = connect_tracked(db)
    try:
        assert conn.execute("SELECT content FROM messages").fetchall() == [
            ("preserved",)
        ]
    finally:
        conn.close()


@pytest.mark.parametrize(
    "count, same, expected",
    [
        (0, True, False),
        (repair._MAX_PERSISTENT_REPAIR_ATTEMPTS - 1, True, False),
        (repair._MAX_PERSISTENT_REPAIR_ATTEMPTS, True, True),
        (str(repair._MAX_PERSISTENT_REPAIR_ATTEMPTS), True, True),
        (1.5, True, False),
        (repair._MAX_PERSISTENT_REPAIR_ATTEMPTS, False, False),
    ],
)
def test_valid_count_and_file_identity_keep_existing_budget(
    ledger_db, count, same, expected
):
    db, fingerprint = ledger_db
    repair._repair_ledger_path(db).write_text(
        json.dumps({
            "fingerprint": fingerprint if same else "different-file",
            "failed_attempts": count,
        }),
        encoding="utf-8",
    )

    assert repair._persistent_repair_attempts_exhausted(db) is expected
    live = repair._db_fingerprint(db) is None
    repair._record_repair_outcome(db, repaired=False)
    recovered = json.loads(repair._repair_ledger_path(db).read_text(encoding="utf-8"))
    # A different file starts a new counter; an unavailable live fingerprint
    # preserves the existing key, as it did before normalization.
    if same or live:
        assert recovered["failed_attempts"] == int(count) + 1
        assert recovered["fingerprint"] == (fingerprint if same else "different-file")
    else:
        assert recovered["failed_attempts"] == 1
        assert recovered["fingerprint"] == fingerprint
