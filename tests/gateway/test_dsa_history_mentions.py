"""Differential history-owner coverage for the digest-selective index (DSA-T1).

Retention must include tool, cron and delegate messages, even though the
interactive trigram search index intentionally excludes those rows.
"""

import hashlib
import multiprocessing
import threading
import json
import random
import sqlite3
from pathlib import Path

from gateway.session_ingress_media import _history_mentions, _history_mentions_scan, release_unheld_media
from hermes_state import SessionDB
from hermes_state_history_fts import (
    BACKFILL_ROWS, HISTORY_FTS_BACKFILL_KEY, HISTORY_FTS_EXACT_READY_KEY,
    HISTORY_FTS_READY_KEY, ensure_history_fts,
)


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
                (("chat", "tool"), "nul: head\x00" + _tail(reference)),
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



def _drop_history_index(conn):
    """Mimic an older store; preserve messages but remove index publication."""
    for trigger in ("messages_history_fts_insert", "messages_history_fts_delete",
                    "messages_history_fts_update"):
        conn.execute("DROP TRIGGER IF EXISTS " + trigger)
    conn.execute("DROP TABLE IF EXISTS messages_history_fts")
    conn.execute("DROP VIEW IF EXISTS messages_history_fts_src")
    conn.execute("DROP TABLE IF EXISTS messages_history_fts_indexed")
    conn.execute("DROP TABLE IF EXISTS messages_history_fts_exact")
    conn.execute("DROP INDEX IF EXISTS idx_messages_history_blob")
    conn.execute("DELETE FROM state_meta WHERE key IN (?, ?, ?)",
                 (HISTORY_FTS_READY_KEY, HISTORY_FTS_BACKFILL_KEY,
                  HISTORY_FTS_EXACT_READY_KEY))


def test_embedded_nul_tail_survives_real_media_release(tmp_path, monkeypatch):
    """P0: GLOB/FTS stops at NUL; SQLite instr and Python see the tail."""
    import gateway.session_ingress_media as media

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    digest = hashlib.sha256(b"nul-retained").hexdigest()
    root = media._media_root()
    path = root / digest / "a%_雪\\named.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\nretained")
    reference = {"sha256": digest, "path": str(path)}

    db = SessionDB(db_path=tmp_path / "state.db")
    try:
        db.create_session("s", source="telegram")
        _insert(db, [("s", "tool", "before\x00" + _tail(reference), 1.0)])
        assert _assert_parity(db, [reference]) == {str(path)}
        assert release_unheld_media(db, [reference]) == 0
        assert path.read_bytes().endswith(b"retained")

        # Simulate a pre-exceptions-index v1 publication: conservative scan
        # still sees the text after the embedded NUL.
        db._execute_write(lambda c: c.execute(
            "DELETE FROM state_meta WHERE key=?", (HISTORY_FTS_EXACT_READY_KEY,)))
        assert _assert_parity(db, [reference]) == {str(path)}
        assert release_unheld_media(db, [reference]) == 0
        assert path.is_file()
    finally:
        db.close()


def test_content_update_below_snapshot_id_cannot_delete_media(tmp_path, monkeypatch):
    """P1: a concurrent writer commits an old-row UPDATE between release phases."""
    import gateway.session_ingress_media as media

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    reference = _reference(tmp_path, "old-row-race", "race.png")
    path = media._media_root() / reference["sha256"] / "race.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"retained")
    reference["path"] = str(path)
    db = SessionDB(db_path=tmp_path / "state.db")
    db.create_session("s", source="telegram")
    _insert(db, [("s", "user", "not yet referenced", 1.0)])

    original_write = db._execute_write
    once = threading.Event()
    committed = threading.Event()
    failures = []
    writer = None

    def update_old_row():
        try:
            original_write(lambda c: c.execute(
                "UPDATE messages SET content=? WHERE id=(SELECT MIN(id) FROM messages)",
                ("now referenced: " + _tail(reference),)))
        except Exception as exc:
            failures.append(exc)
        finally:
            committed.set()

    def raced_collect(fn, patience_s=None):
        nonlocal writer
        # This hook is entered only after the outer read snapshot has closed,
        # but before the media deletion transaction obtains its writer lock.
        if not once.is_set():
            once.set()
            writer = threading.Thread(target=update_old_row, daemon=True)
            writer.start()
            assert committed.wait(10), "concurrent update did not commit before deletion"
            assert not failures, failures
        return original_write(fn, patience_s=patience_s)

    monkeypatch.setattr(db, "_execute_write", raced_collect)
    try:
        assert release_unheld_media(db, [reference]) == 0
        assert once.is_set() and committed.is_set()
        assert path.is_file(), "updated transcript lost its retained file"
        assert _assert_parity(db, [reference]) == {str(path)}
    finally:
        if writer is not None:
            writer.join(timeout=10)
        db.close()

def test_incremental_disk_backfill_resumes_with_mutations_and_large_rows(tmp_path):
    """P1 migration: checkpoint stays durable, ready is atomic, edits not lost."""
    reference = _reference(tmp_path, "disk-backfill", "report%_雪.txt")
    db_path = tmp_path / "state.db"
    db = SessionDB(db_path=db_path)
    try:
        db.create_session("s", source="cron")
        db._execute_write(_drop_history_index)
        rows = []
        for i in range(BACKFILL_ROWS * 3):
            text = ("large tool output " + "雪" * 40_000) if i % 19 == 0 else "other " + str(i)
            if i == 1:
                text += "\x00" + _tail(reference)
            rows.append(("s", "tool", text, float(i)))
        _insert(db, rows)
    finally:
        db.close()

    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    reader = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    try:
        reader.execute("BEGIN")
        snapshot_count = reader.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        ensure_history_fts(conn.cursor(), enabled=True)
        assert conn.execute(
            "SELECT 1 FROM state_meta WHERE key=?",
            (HISTORY_FTS_READY_KEY,)).fetchone() is None
        progress = int(conn.execute(
            "SELECT value FROM state_meta WHERE key=?",
            (HISTORY_FTS_BACKFILL_KEY,)).fetchone()[0])
        assert 0 < progress < len(rows), "first-open migration must not scan all history"
        assert _history_mentions(conn, [reference]) == {reference["path"]}
        # Reopen a real disk connection: progress must survive process lifetime.
        conn.close()
        conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
        ensure_history_fts(conn.cursor(), enabled=True)
        resumed = int(conn.execute(
            "SELECT value FROM state_meta WHERE key=?",
            (HISTORY_FTS_BACKFILL_KEY,)).fetchone()[0])
        assert resumed > progress

        # Modify an already-backfilled id, delete another indexed id and
        # create a high-id mention. Staging triggers must avoid double indexes.
        conn.execute("UPDATE messages SET content=? WHERE id=1",
                     ("updated after checkpoint: " + _tail(reference),))
        conn.execute("DELETE FROM messages WHERE id=2")
        conn.execute(
            "INSERT INTO messages(session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            ("s", "tool", "\x00" + _tail(reference), 9999.0))
        assert reader.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == snapshot_count
        reader.execute("ROLLBACK")

        for _ in range(200):
            if conn.execute("SELECT value FROM state_meta WHERE key=?",
                            (HISTORY_FTS_READY_KEY,)).fetchone():
                break
            ensure_history_fts(conn.cursor(), enabled=True)
        assert conn.execute(
            "SELECT value FROM state_meta WHERE key=?",
            (HISTORY_FTS_READY_KEY,)).fetchone() == ("1",)
        assert conn.execute(
            "SELECT value FROM state_meta WHERE key=?",
            (HISTORY_FTS_EXACT_READY_KEY,)).fetchone() == ("1",)
        assert conn.execute(
            "SELECT 1 FROM state_meta WHERE key=?",
            (HISTORY_FTS_BACKFILL_KEY,)).fetchone() is None
        assert _history_mentions(conn, [reference]) == _history_mentions_scan(conn, [reference])
        assert _history_mentions(conn, [reference]) == {reference["path"]}
        assert conn.execute(
            "SELECT COUNT(*) FROM messages_history_fts WHERE messages_history_fts MATCH ?",
            ('"' + reference["sha256"] + '"',)).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM messages_history_fts_exact",
        ).fetchone()[0] == 1
    finally:
        if reader.in_transaction:
            reader.execute("ROLLBACK")
        reader.close()
        conn.close()


def _migrator_in_another_process(db_path, start, outcome):
    """Each process owns an independent SQLite connection and writer lease."""
    conn = sqlite3.connect(db_path, timeout=15, isolation_level=None)
    try:
        assert start.wait(12), "migrator was never released"
        for _ in range(3):
            ensure_history_fts(conn.cursor(), enabled=True)
        outcome.put(None)
    except BaseException as exc:
        outcome.put(repr(exc))
    finally:
        conn.close()


def test_competing_processes_migrate_once_on_disk(tmp_path):
    """P1 migration: independent startup processes resume without double postings."""
    db_path = tmp_path / "migrating.db"
    conn = sqlite3.connect(db_path, isolation_level=None)
    reference = _reference(tmp_path, "other-process", "worker.txt")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE state_meta(key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("CREATE TABLE messages(id INTEGER PRIMARY KEY, content TEXT)")
        conn.executemany(
            "INSERT INTO messages(content) VALUES (?)",
            [(("row " + str(i) + (" " + _tail(reference) if i % 101 == 0 else "")),)
             for i in range(BACKFILL_ROWS * 3)])
    finally:
        conn.close()

    ctx = multiprocessing.get_context("spawn")
    start = ctx.Event()
    outcomes = ctx.Queue()
    processes = [ctx.Process(target=_migrator_in_another_process,
                             args=(str(db_path), start, outcomes)) for _ in range(2)]
    for p in processes:
        p.start()
    start.set()
    try:
        results = [outcomes.get(timeout=20) for _ in processes]
        for p in processes:
            p.join(timeout=20)
        assert results == [None, None], results
        assert all(p.exitcode == 0 for p in processes)
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
            p.join(timeout=5)
        outcomes.close()

    conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
    try:
        while conn.execute(
                "SELECT 1 FROM state_meta WHERE key=?",
                (HISTORY_FTS_READY_KEY,)).fetchone() is None:
            ensure_history_fts(conn.cursor(), enabled=True)
        assert _history_mentions(conn, [reference]) == _history_mentions_scan(conn, [reference])
        assert conn.execute(
            "SELECT COUNT(*) FROM messages_history_fts WHERE messages_history_fts MATCH ?",
            ('"' + reference["sha256"] + '"',)).fetchone()[0] == 4
    finally:
        conn.close()


def test_disk_many_digest_candidates_and_tool_updates_preserve_exact_matches(tmp_path):
    """P2: realistic long outputs and many candidate digests have exact parity."""
    db = SessionDB(db_path=tmp_path / "many.db")
    try:
        db.create_session("s", source="subagent")
        refs = [_reference(tmp_path, i, f"file%_{i}\\雪.txt") for i in range(128)]
        _insert(db, [
            ("s", "tool", "tool_output=" + "雪" * 2048 +
             ("\x00" if i % 17 == 0 else "") + _tail(refs[i]), float(i))
            for i in range(len(refs))
        ])
        assert _assert_parity(db, refs) == {r["path"] for r in refs}
        db._execute_write(lambda c: c.execute(
            "UPDATE messages SET content=? WHERE id=1",
            ("updated " + _tail(refs[-1]),)))
        expected = _assert_parity(db, refs)
        assert expected == {r["path"] for r in refs[1:]}
        assert _assert_parity(db, refs, 64) == {r["path"] for r in refs[64:]}
    finally:
        db.close()



def test_missing_fts_trigger_downgrades_to_exact_scan(tmp_path):
    """A stale ready marker alone cannot authorize a potentially unsafe index."""
    reference = _reference(tmp_path, "missing-trigger", "path_%.png")
    db = SessionDB(db_path=tmp_path / "missing-trigger.db")
    try:
        db.create_session("s", source="telegram")
        db._execute_write(lambda c: c.execute(
            "DROP TRIGGER messages_history_fts_insert"))
        _insert(db, [("s", "tool", "reference: " + _tail(reference), 1.0)])
        with db._read_ctx() as conn:
            assert conn.execute(
                "SELECT value FROM state_meta WHERE key=?",
                (HISTORY_FTS_READY_KEY,)).fetchone() == ("1",)
            assert _history_mentions(conn, [reference]) == _history_mentions_scan(
                conn, [reference]) == {reference["path"]}
    finally:
        db.close()
