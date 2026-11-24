"""The decision ledger: explicit user approvals, denials, corrections and preferences, kept verbatim per session.

Rows are evidence for the compaction handoff, never an executable approval gate. The caller bounds and redacts
the text (agent.decision_ledger.record_decision); this module keeps the newest window per session, with
denials, corrections and approvals retained ahead of preferences.

``pin`` rows are the user's ``/pin`` entries (agent.pins). They are written only by the pin verbs, which take a
cap and refuse an add past it; the window trim never touches them.
"""

from __future__ import annotations

import time

from persistence.sqlite._holder import StoreHolder

MAX_LEDGER_ENTRIES = 50
LEDGER_KINDS = ("approval", "denial", "correction", "preference")

_TRIM_SQL = """DELETE FROM decision_ledger WHERE session_id = ? AND kind != 'pin' AND id NOT IN (
    SELECT id FROM decision_ledger WHERE session_id = ? AND kind != 'pin'
    ORDER BY CASE kind WHEN 'denial' THEN 0 WHEN 'correction' THEN 1
        WHEN 'approval' THEN 2 ELSE 3 END, created_at DESC, turn_id DESC, text DESC, id DESC LIMIT ?)"""


def _trim(conn, session_id: str) -> None:
    conn.execute(_TRIM_SQL, (session_id, session_id, MAX_LEDGER_ENTRIES))


def append_decision_ledger_entry(holder: StoreHolder, session_id: str, kind: str, text: str, *, turn_id: str = "") -> None:
    if kind not in LEDGER_KINDS:
        raise ValueError(f"Unsupported decision ledger kind: {kind!r}")
    if not isinstance(text, str) or not text:
        return

    def _append(conn) -> None:
        conn.execute(
            "INSERT INTO decision_ledger (session_id, turn_id, kind, text, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, turn_id or "", kind, text, time.time()),
        )
        _trim(conn, session_id)

    holder._execute_write(_append)


def get_decision_ledger_entries(holder: StoreHolder, session_id: str) -> list[dict[str, str]]:
    with holder._read_ctx() as conn:
        rows = conn.execute(
            "SELECT turn_id, kind, text FROM decision_ledger WHERE session_id = ? ORDER BY created_at ASC, id ASC",
            (session_id,),
        ).fetchall()
    return [{"turn_id": str(row["turn_id"] or ""), "kind": row["kind"], "text": row["text"]} for row in rows]


def copy_decision_ledger_entries(holder: StoreHolder, parent_session_id: str, child_session_id: str) -> None:
    """Carry the parent's window to a compression child; a retry adds nothing already copied."""

    def _copy(conn) -> None:
        conn.execute(
            """INSERT INTO decision_ledger (session_id, turn_id, kind, text, created_at)
               SELECT ?, parent.turn_id, parent.kind, parent.text, parent.created_at
               FROM decision_ledger AS parent
               WHERE parent.session_id = ?
                 AND NOT EXISTS (
                     SELECT 1 FROM decision_ledger AS child
                     WHERE child.session_id = ?
                       AND child.turn_id = parent.turn_id
                       AND child.kind = parent.kind
                       AND child.text = parent.text
                       AND child.created_at = parent.created_at
                 )
               ORDER BY parent.id ASC""",
            (child_session_id, parent_session_id, child_session_id),
        )
        _trim(conn, child_session_id)

    holder._execute_write(_copy)


def _pin_ids(conn, session_id: str) -> list[int]:
    return [row["id"] for row in conn.execute(
        "SELECT id FROM decision_ledger WHERE session_id = ? AND kind = 'pin' ORDER BY id ASC", (session_id,))]


def add_pin(holder: StoreHolder, session_id: str, text: str, *, limit: int):
    """Append one pin and return its 1-based number, or None (nothing written) when ``limit`` pins exist."""

    def _add(conn):
        count = len(_pin_ids(conn, session_id))
        if count >= limit:
            return None
        conn.execute(
            "INSERT INTO decision_ledger (session_id, turn_id, kind, text, created_at) VALUES (?, '', 'pin', ?, ?)",
            (session_id, text, time.time()),
        )
        return count + 1

    return holder._execute_write(_add)


def remove_pin(holder: StoreHolder, session_id: str, number: int):
    """Delete pin ``number`` (1-based) and return its text, or None when there is no such pin."""

    def _remove(conn):
        ids = _pin_ids(conn, session_id)
        if not isinstance(number, int) or not 1 <= number <= len(ids):
            return None
        row = conn.execute("SELECT text FROM decision_ledger WHERE id = ?", (ids[number - 1],)).fetchone()
        conn.execute("DELETE FROM decision_ledger WHERE id = ?", (ids[number - 1],))
        return row["text"]

    return holder._execute_write(_remove)


def patch_pin(holder: StoreHolder, session_id: str, number: int, text: str) -> bool:
    """Replace pin ``number``'s text in place (its number is kept); False when there is no such pin."""

    def _patch(conn):
        ids = _pin_ids(conn, session_id)
        if not isinstance(number, int) or not 1 <= number <= len(ids):
            return False
        conn.execute("UPDATE decision_ledger SET text = ? WHERE id = ?", (text, ids[number - 1]))
        return True

    return bool(holder._execute_write(_patch))
