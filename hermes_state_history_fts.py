"""Durable, bounded FTS5 candidate index for exact transcript media retention.

Every transcript role is included. FTS candidates are *never* sufficient to
release media: callers always verify literal tails; BLOB/NUL text is checked
exactly because SQLite GLOB/FTS tokenization can stop at embedded NULs.

For an existing database, each open indexes at most BACKFILL_ROWS rows or
BACKFILL_BYTES of content in one short transaction. A durable high-water mark
and staged triggers preserve edits between opens. Until atomic publication of
the ready marker, consumers use the original exact transcript scan.
"""

import sqlite3


HISTORY_FTS_READY_KEY = "media_history_fts_ready_v1"
HISTORY_FTS_BACKFILL_KEY = "media_history_fts_backfill_id_v1"
HISTORY_FTS_EXACT_READY_KEY = "media_history_fts_exact_ready_v1"
BACKFILL_ROWS = 128
BACKFILL_BYTES = 256 * 1024
_HISTORY_GLOB = "*" + "[0-9a-f]" * 64 + "*"
_TRIGGERS = (
    "messages_history_fts_insert",
    "messages_history_fts_delete",
    "messages_history_fts_update",
)
_OBJECTS = frozenset((*_TRIGGERS, "messages_history_fts", "messages_history_fts_src"))


def _indexed_content(alias: str) -> str:
    return (f"CASE WHEN typeof({alias}.content) = 'text' "
            f"AND {alias}.content GLOB '{_HISTORY_GLOB}' THEN {alias}.content END")


def _objects(cursor: sqlite3.Cursor) -> set[str]:
    return {row[0] for row in cursor.execute(
        "SELECT name FROM sqlite_master WHERE name LIKE 'messages_history_fts%'")}


def _is_ready(cursor: sqlite3.Cursor) -> bool:
    return (_OBJECTS.issubset(_objects(cursor))
            and cursor.execute("SELECT 1 FROM state_meta WHERE key=? AND value='1'",
                               (HISTORY_FTS_READY_KEY,)).fetchone() is not None)


def history_fts_ready(cursor: sqlite3.Cursor) -> bool:
    """Check both publication marker and required index/trigger objects."""
    return _is_ready(cursor)


def _exact_insert(alias: str) -> str:
    return (
        "INSERT OR IGNORE INTO messages_history_fts_exact(id) "
        f"SELECT {alias}.id WHERE typeof({alias}.content)='blob' "
        f"OR (typeof({alias}.content)='text' "
        f"AND instr({alias}.content, char(0))>0);"
    )


def _fts_delete(alias: str, *, staged: bool) -> str:
    if staged:
        return (
            "INSERT INTO messages_history_fts(messages_history_fts, rowid, content) "
            f"SELECT 'delete', {alias}.id, {_indexed_content(alias)} "
            "WHERE EXISTS (SELECT 1 FROM messages_history_fts_indexed "
            f"WHERE id={alias}.id);"
        )
    return (
        "INSERT INTO messages_history_fts(messages_history_fts, rowid, content) "
        f"VALUES ('delete', {alias}.id, {_indexed_content(alias)});"
    )


def _install_triggers(cursor: sqlite3.Cursor, *, staged: bool) -> None:
    """Staging tracks which rowids have been indexed, preventing double inserts.

    At completion the tracking table and conditional triggers are replaced
    atomically by the smaller permanent trigger set.
    """
    for name in _TRIGGERS:
        cursor.execute(f"DROP TRIGGER IF EXISTS {name}")
    mark_new = ("INSERT OR IGNORE INTO messages_history_fts_indexed(id) "
                "VALUES (new.id);" if staged else "")
    drop_old = ("DELETE FROM messages_history_fts_indexed WHERE id=old.id;"
                if staged else "")
    cursor.execute(
        "CREATE TRIGGER messages_history_fts_insert AFTER INSERT ON messages BEGIN "
        "INSERT INTO messages_history_fts(rowid, content) "
        f"VALUES (new.id, {_indexed_content('new')}); "
        f"{mark_new} {_exact_insert('new')} END")
    cursor.execute(
        "CREATE TRIGGER messages_history_fts_delete AFTER DELETE ON messages BEGIN "
        f"{_fts_delete('old', staged=staged)} "
        "DELETE FROM messages_history_fts_exact WHERE id=old.id; "
        f"{drop_old} END")
    cursor.execute(
        "CREATE TRIGGER messages_history_fts_update AFTER UPDATE OF content ON messages "
        "WHEN old.content IS NOT new.content BEGIN "
        f"{_fts_delete('old', staged=staged)} "
        "INSERT INTO messages_history_fts(rowid, content) "
        f"VALUES (new.id, {_indexed_content('new')}); "
        f"{mark_new} "
        "DELETE FROM messages_history_fts_exact WHERE id=old.id; "
        f"{_exact_insert('new')} END")


def _begin_backfill(cursor: sqlite3.Cursor) -> None:
    """Create empty index and synchronous mutation tracking; never scan all rows."""
    for name in _TRIGGERS:
        cursor.execute(f"DROP TRIGGER IF EXISTS {name}")
    # No ready marker is exposed while a new projection is constructed.
    # Replacing an incomplete old attempt is safe because readers scan.
    cursor.execute("DROP TABLE IF EXISTS messages_history_fts")
    cursor.execute("DROP VIEW IF EXISTS messages_history_fts_src")
    cursor.execute("DROP TABLE IF EXISTS messages_history_fts_indexed")
    cursor.execute("DROP TABLE IF EXISTS messages_history_fts_exact")
    cursor.execute(
        "CREATE VIEW messages_history_fts_src AS "
        f"SELECT id, {_indexed_content('messages')} AS content FROM messages")
    cursor.execute(
        "CREATE VIRTUAL TABLE messages_history_fts USING fts5("
        "content, content='messages_history_fts_src', content_rowid='id', "
        "tokenize='trigram')")
    cursor.execute(
        "CREATE TABLE messages_history_fts_indexed(id INTEGER PRIMARY KEY)")
    cursor.execute(
        "CREATE TABLE messages_history_fts_exact(id INTEGER PRIMARY KEY)")
    _install_triggers(cursor, staged=True)
    cursor.execute(
        "INSERT INTO state_meta(key, value) VALUES (?, 'start') "
        "ON CONFLICT(key) DO UPDATE SET value='start'",
        (HISTORY_FTS_BACKFILL_KEY,))
    cursor.execute("DELETE FROM state_meta WHERE key IN (?, ?)",
                   (HISTORY_FTS_READY_KEY, HISTORY_FTS_EXACT_READY_KEY))


def _advance_backfill(cursor: sqlite3.Cursor, last_id: int | None) -> None:
    """Bound a writer transaction in both rows and source bytes.

    Trigger-maintained rows are skipped using the staging PK. The SQL view
    projection is also used here so the FTS tokenizer sees identical text.
    """
    query = (
        "SELECT m.id, " + _indexed_content("m") + ", "
        "(typeof(m.content)='blob' OR "
        "(typeof(m.content)='text' AND instr(m.content, char(0))>0)), "
        "coalesce(length(CAST(m.content AS blob)), 0) "
        "FROM messages AS m "
    )
    if last_id is None:
        scan = cursor.connection.execute(query + "ORDER BY m.id LIMIT ?", (BACKFILL_ROWS,))
    else:
        scan = cursor.connection.execute(
            query + "WHERE m.id>? ORDER BY m.id LIMIT ?", (last_id, BACKFILL_ROWS))
    processed = 0
    total_bytes = 0
    try:
        for row_id, projected, exceptional, size in scan:
            if processed and total_bytes + size > BACKFILL_BYTES:
                break
            # If a live INSERT/UPDATE already indexed this row, do not index
            # it twice. All checks/writes happen under the same writer lock.
            cursor.execute(
                "INSERT INTO messages_history_fts(rowid, content) "
                "SELECT ?, ? WHERE NOT EXISTS ("
                "SELECT 1 FROM messages_history_fts_indexed WHERE id=?)",
                (row_id, projected, row_id))
            cursor.execute(
                "INSERT OR IGNORE INTO messages_history_fts_indexed(id) VALUES (?)",
                (row_id,))
            if exceptional:
                cursor.execute(
                    "INSERT OR IGNORE INTO messages_history_fts_exact(id) VALUES (?)",
                    (row_id,))
            last_id = row_id
            processed += 1
            total_bytes += size
    finally:
        scan.close()
    cursor.execute(
        "UPDATE state_meta SET value=? WHERE key=?",
        (str(last_id) if last_id is not None else "start", HISTORY_FTS_BACKFILL_KEY))

    remaining = cursor.execute(
        "SELECT 1 FROM messages LIMIT 1" if last_id is None
        else "SELECT 1 FROM messages WHERE id>? LIMIT 1",
        () if last_id is None else (last_id,)).fetchone()
    if remaining is not None:
        return
    # No message can change between the final indexed row and marker commit
    # because this transaction owns SQLite's writer lock.
    _install_triggers(cursor, staged=False)
    cursor.execute("DROP TABLE messages_history_fts_indexed")
    cursor.execute("DELETE FROM state_meta WHERE key=?", (HISTORY_FTS_BACKFILL_KEY,))
    cursor.executemany(
        "INSERT INTO state_meta(key, value) VALUES (?, '1') "
        "ON CONFLICT(key) DO UPDATE SET value='1'",
        ((HISTORY_FTS_READY_KEY,), (HISTORY_FTS_EXACT_READY_KEY,)))


def ensure_history_fts(cursor: sqlite3.Cursor, *, enabled: bool) -> None:
    """Resume one durable batch, publishing readiness only after all rows.

    Existing ready-v1 installations remain readable, with an exact NUL fallback
    if they predate the sparse exceptions table. Disabled runtimes remove
    triggers and readiness, so all history checks revert to the exact scan.
    """
    if enabled and _is_ready(cursor):
        return
    if not enabled and not (_objects(cursor) & set(_TRIGGERS)) and not cursor.execute(
            "SELECT 1 FROM state_meta WHERE key IN (?, ?, ?) LIMIT 1",
            (HISTORY_FTS_READY_KEY, HISTORY_FTS_BACKFILL_KEY, HISTORY_FTS_EXACT_READY_KEY)).fetchone():
        return

    nested = cursor.connection.in_transaction
    cursor.execute("SAVEPOINT media_history_fts" if nested else "BEGIN IMMEDIATE")
    try:
        if enabled and not _is_ready(cursor):
            progress = cursor.execute(
                "SELECT value FROM state_meta WHERE key=?",
                (HISTORY_FTS_BACKFILL_KEY,)).fetchone()
            if progress is None:
                _begin_backfill(cursor)
                last_id = None
            else:
                last_id = None if progress[0] == 'start' else int(progress[0])
            _advance_backfill(cursor, last_id)
        elif not enabled:
            for name in _TRIGGERS:
                cursor.execute(f"DROP TRIGGER IF EXISTS {name}")
            cursor.execute(
                "DELETE FROM state_meta WHERE key IN (?, ?, ?)",
                (HISTORY_FTS_READY_KEY, HISTORY_FTS_BACKFILL_KEY, HISTORY_FTS_EXACT_READY_KEY))
        cursor.execute("RELEASE SAVEPOINT media_history_fts" if nested else "COMMIT")
    except BaseException:
        if nested:
            cursor.execute("ROLLBACK TO SAVEPOINT media_history_fts")
            cursor.execute("RELEASE SAVEPOINT media_history_fts")
        else:
            cursor.execute("ROLLBACK")
        raise
