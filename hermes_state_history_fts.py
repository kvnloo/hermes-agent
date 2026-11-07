"""Digest-selective FTS5 index for exact transcript media-retention checks.

The interactive search trigram index intentionally omits tool, cron and delegate
content. Media retention must see ALL message rows. This separate index covers
only text containing a full lowercase SHA-256 candidate; it is maintained by
SQLite triggers, including INSERT ... SELECT (branch/compression) and updates.
"""

import sqlite3


HISTORY_FTS_READY_KEY = "media_history_fts_ready_v1"
_HISTORY_GLOB = "*" + "[0-9a-f]" * 64 + "*"
_TRIGGERS = (
    "messages_history_fts_insert",
    "messages_history_fts_delete",
    "messages_history_fts_update",
)
_OBJECTS = frozenset((*_TRIGGERS, "messages_history_fts", "messages_history_fts_src",
                      "idx_messages_history_blob"))


def _indexed_content(alias: str) -> str:
    return (f"CASE WHEN typeof({alias}.content) = 'text' "
            f"AND {alias}.content GLOB '{_HISTORY_GLOB}' THEN {alias}.content END")


def _objects(cursor: sqlite3.Cursor) -> set[str]:
    return {row[0] for row in cursor.execute(
        "SELECT name FROM sqlite_master WHERE name LIKE 'messages_history_fts%' "
        "OR name = 'idx_messages_history_blob'")}


def _is_ready(cursor: sqlite3.Cursor) -> bool:
    return (_OBJECTS.issubset(_objects(cursor))
            and cursor.execute("SELECT 1 FROM state_meta WHERE key=? AND value='1'",
                               (HISTORY_FTS_READY_KEY,)).fetchone() is not None)


def ensure_history_fts(cursor: sqlite3.Cursor, *, enabled: bool) -> None:
    """Build/backfill exactly once, atomically with trigger publication and the ready marker.

    BEGIN IMMEDIATE serializes competing startup writers; WAL readers continue on
    their original snapshots. No reader uses an unbackfilled index: the marker is
    published only with the complete rebuilt index and all three triggers.
    On runtimes without the trigram tokenizer, detach triggers AND clear the marker
    so older/unsupported writers can continue and readers use the exact scan.
    """
    if enabled and _is_ready(cursor):
        return
    if not enabled and not (_objects(cursor) & set(_TRIGGERS)) and not cursor.execute(
            "SELECT 1 FROM state_meta WHERE key=?", (HISTORY_FTS_READY_KEY,)).fetchone():
        return

    nested = cursor.connection.in_transaction
    cursor.execute("SAVEPOINT media_history_fts" if nested else "BEGIN IMMEDIATE")
    try:
        # Recheck under the writer lock: another process may have completed
        # the migration between our first probe and this lock acquisition.
        if enabled and not _is_ready(cursor):
            cursor.execute(
                f"CREATE VIEW IF NOT EXISTS messages_history_fts_src AS "
                f"SELECT id, {_indexed_content('messages')} AS content FROM messages")
            cursor.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS messages_history_fts USING fts5("
                "content, content='messages_history_fts_src', content_rowid='id', "
                "tokenize='trigram')")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_history_blob "
                "ON messages(id) WHERE typeof(content) = 'blob'")
            cursor.execute(
                "CREATE TRIGGER IF NOT EXISTS messages_history_fts_insert "
                "AFTER INSERT ON messages BEGIN "
                "INSERT INTO messages_history_fts(rowid, content) "
                f"VALUES (new.id, {_indexed_content('new')}); END")
            cursor.execute(
                "CREATE TRIGGER IF NOT EXISTS messages_history_fts_delete "
                "AFTER DELETE ON messages BEGIN "
                "INSERT INTO messages_history_fts(messages_history_fts, rowid, content) "
                f"VALUES ('delete', old.id, {_indexed_content('old')}); END")
            cursor.execute(
                "CREATE TRIGGER IF NOT EXISTS messages_history_fts_update "
                "AFTER UPDATE OF content ON messages "
                "WHEN old.content IS NOT new.content BEGIN "
                "INSERT INTO messages_history_fts(messages_history_fts, rowid, content) "
                f"VALUES ('delete', old.id, {_indexed_content('old')}); "
                "INSERT INTO messages_history_fts(rowid, content) "
                f"VALUES (new.id, {_indexed_content('new')}); END")
            # Rebuild from the external-content view. A missing trigger or an
            # interrupted older bootstrap must never expose a partial index.
            cursor.execute(
                "INSERT INTO messages_history_fts(messages_history_fts) VALUES('rebuild')")
            cursor.execute(
                "INSERT INTO state_meta(key, value) VALUES (?, '1') "
                "ON CONFLICT(key) DO UPDATE SET value='1'", (HISTORY_FTS_READY_KEY,))
        elif not enabled:
            for name in _TRIGGERS:
                cursor.execute(f"DROP TRIGGER IF EXISTS {name}")
            cursor.execute("DELETE FROM state_meta WHERE key=?", (HISTORY_FTS_READY_KEY,))
        cursor.execute("RELEASE SAVEPOINT media_history_fts" if nested else "COMMIT")
    except BaseException:
        if nested:
            cursor.execute("ROLLBACK TO SAVEPOINT media_history_fts")
            cursor.execute("RELEASE SAVEPOINT media_history_fts")
        else:
            cursor.execute("ROLLBACK")
        raise
