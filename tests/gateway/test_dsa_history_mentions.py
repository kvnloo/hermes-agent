"""Differential history-owner coverage for the digest-selective index (DSA-T1).

Retention must include tool, cron and delegate messages, even though the
interactive trigram search index intentionally excludes those rows.
"""

import hashlib
import json
import random
import sqlite3
from pathlib import Path

from gateway.session_ingress_media import _history_mentions, _history_mentions_scan
from hermes_state import SessionDB
from hermes_state_history_fts import HISTORY_FTS_READY_KEY


def _reference(tmp_path, key, name):
    digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
    return {"sha256": digest, "path": str(tmp_path / "native-inputs" / digest / name)}


def _tail(reference, separator="/"):
    return reference["sha256"] + separator + Path(reference["path"]).name


def _assert_parity(db, references, after_id=0):
    with db._read_ctx() as conn:
        expected = _history_mentions_scan(conn, references, after_id)
        assert _history_mentions(conn, references, after_id) == expected
        return expected


def _insert(db, rows):
    return db._execute_write(
        lambda conn: conn.executemany(
            "INSERT INTO messages(session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            rows,
        )
    )


def test_generated_transcripts_match_full_scan_with_special_paths(tmp_path):
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        for session, source in (("chat", "telegram"), ("scheduled", "cron"), ("child", "subagent")):
            db.create_session(session, source=source)
        names = ("normal.png", "literal%_wildcard_文件.png", r"nested\quoted_name.txt", "雪☃.pdf")
        references = [_reference(tmp_path, i, name) for i, name in enumerate(names)]
        # Duplicate candidates, arbitrary Unicode, path separators, JSON-escaped
        # backslashes, and %/_ characters are treated as literal substrings.
        rng = random.Random(1107)
        rows = []
        forced = []
        for i, reference in enumerate(references):
            raw = reference["path"]
            forced.extend((
                (("chat", "user"), "raw: " + raw),
                (("scheduled", "tool"), "visible: " + _tail(reference)),
                (("child", "assistant"), "json: " + json.dumps({"file": raw}, ensure_ascii=True)),
                (("chat", "tool"), "escaped: " + json.dumps(_tail(reference, "\\"))),
            ))
        for i, ((session, role), content) in enumerate(forced):
            rows.append((session, role, content, float(i)))
        for i in range(520):
            reference = rng.choice(references)
            variant = rng.randrange(10)
            if variant == 0:
                content = "link " + _tail(reference) + " \u03b2"
            elif variant == 1:
                content = json.dumps({"path": reference["path"]}, ensure_ascii=True)
            elif variant == 2:
                content = "sandbox " + _tail(reference, "\\")
            elif variant == 3:
                content = "sha only " + reference["sha256"]  # never sufficient by itself
            elif variant == 4:
                content = json.dumps(_tail(reference, "\\"), ensure_ascii=True)
            elif variant == 5:
                content = "wildcards % and _ are not pattern operators"
            elif variant == 6:
                content = "\u2603\u96ea" + str(i)
            elif variant == 7:
                content = ""
            elif variant == 8:
                content = None
            else:
                content = ("blob " + _tail(reference)).encode("utf-8")
            session = ("chat", "scheduled", "child")[rng.randrange(3)]
            role = ("user", "assistant", "tool")[rng.randrange(3)]
            rows.append((session, role, content, float(1000 + i)))
        _insert(db, rows)

        with db._read_ctx() as conn:
            marker = conn.execute(
                "SELECT value FROM state_meta WHERE key=?", (HISTORY_FTS_READY_KEY,)
            ).fetchone()
            if marker is not None:
                assert marker[0] == "1"
                assert conn.execute(
                    "SELECT COUNT(*) FROM messages_history_fts WHERE messages_history_fts MATCH ?",
                    ('"' + references[0]["sha256"] + '"',),
                ).fetchone()[0] > 0

        for candidates in (
            [], references, references[:2], references[2:],
            [references[0], references[0]], [references[3], references[1]],
        ):
            for after_id in (0, 1, 8, 25, 245, 550, 100000):
                _assert_parity(db, candidates, after_id)
        assert _assert_parity(db, references) == {ref["path"] for ref in references}
        assert _assert_parity(db, references, 100000) == set()

        # The production caller validates canonical 64-hex SHA values, but the
        # lookup itself must not introduce false negatives for legacy callers.
        foreign = {"sha256": "literal%_digest", "path": str(tmp_path / "literal%_digest" / "x")}
        _assert_parity(db, [foreign, references[0]])
        _assert_parity(db, [foreign])
    finally:
        db.close()


def test_insert_copy_update_delete_and_id_watermark(tmp_path):
    reference = _reference(tmp_path, "copied", "file%_with\\slash.txt")
    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        db.create_session("a", source="telegram")
        db.create_session("b", source="telegram")
        _insert(db, [("a", "user", "no matching file", 1.0)])
        with db._read_ctx() as conn:
            watermark = conn.execute("SELECT MAX(id) FROM messages").fetchone()[0]
        assert _assert_parity(db, [reference], watermark) == set()

        _insert(db, [("a", "tool", "resource " + _tail(reference), 2.0)])
        assert _assert_parity(db, [reference], watermark) == {reference["path"]}
        with db._read_ctx() as conn:
            source_id = conn.execute("SELECT MAX(id) FROM messages").fetchone()[0]

        # Copying via INSERT ... SELECT (a branch/compress style writer) must
        # maintain the index even if it never uses the SessionDB append API.
        db._execute_write(lambda conn: conn.execute(
            "INSERT INTO messages(session_id, role, content, timestamp) "
            "SELECT ?, role, content, ? FROM messages WHERE id=?",
            ("b", 3.0, source_id),
        ))
        assert _assert_parity(db, [reference], source_id) == {reference["path"]}

        db._execute_write(lambda conn: conn.execute(
            "UPDATE messages SET content=? WHERE id=?", ("redacted", source_id)
        ))
        assert _assert_parity(db, [reference]) == {reference["path"]}
        db._execute_write(lambda conn: conn.execute(
            "DELETE FROM messages WHERE id>?", (source_id,)
        ))
        assert _assert_parity(db, [reference]) == set()

        db._execute_write(lambda conn: conn.execute(
            "UPDATE messages SET content=? WHERE id=1", ("restored " + _tail(reference),)
        ))
        assert _assert_parity(db, [reference]) == {reference["path"]}
        assert _assert_parity(db, [reference], watermark) == set()
    finally:
        db.close()


def test_existing_database_backfill_is_idempotent_and_reader_safe(tmp_path):
    reference = _reference(tmp_path, "migration", "quoted%_雪.png")
    db_path = tmp_path / "state.db"
    db = SessionDB(db_path=db_path)
    try:
        db.create_session("a", source="telegram")
        _insert(db, [("a", "user", "old: " + _tail(reference), 1.0)])
        # Model an old DB where historical messages exist but the new index has
        # not been installed. A subsequent writer adds a row without triggers.
        def detach(conn):
            for trigger in ("messages_history_fts_insert", "messages_history_fts_delete",
                            "messages_history_fts_update"):
                conn.execute("DROP TRIGGER IF EXISTS " + trigger)
            conn.execute("DROP TABLE IF EXISTS messages_history_fts")
            conn.execute("DROP VIEW IF EXISTS messages_history_fts_src")
            conn.execute("DROP INDEX IF EXISTS idx_messages_history_blob")
            conn.execute("DELETE FROM state_meta WHERE key=?", (HISTORY_FTS_READY_KEY,))
        db._execute_write(detach)
        _insert(db, [("a", "tool", "new: " + _tail(reference, "\\"), 2.0)])
        assert _assert_parity(db, [reference]) == {reference["path"]}
    finally:
        db.close()

    # A reader that started before migration must observe its original
    # snapshot, not a half-backfilled index or partially installed triggers.
    reader = sqlite3.connect(db_path, isolation_level=None)
    reader.execute("BEGIN")
    before = reader.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    reopened = SessionDB(db_path=db_path)
    try:
        assert reader.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == before
        assert _assert_parity(reopened, [reference]) == {reference["path"]}
        with reopened._read_ctx() as conn:
            marker = conn.execute(
                "SELECT value FROM state_meta WHERE key=?", (HISTORY_FTS_READY_KEY,)
            ).fetchone()
            if marker:
                assert marker[0] == "1"
                assert conn.execute(
                    "SELECT count(*) FROM messages_history_fts WHERE messages_history_fts MATCH ?",
                    ('"' + reference["sha256"] + '"',),
                ).fetchone()[0] == 2
    finally:
        reader.execute("ROLLBACK")
        reader.close()
        reopened.close()

    again = SessionDB(db_path=db_path)
    try:
        assert _assert_parity(again, [reference]) == {reference["path"]}
    finally:
        again.close()
