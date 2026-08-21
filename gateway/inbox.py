"""Durable gateway inbox and canonical turn queue.

The only hand-off boundary is :meth:`commit_turn`: it creates the durable turn
and marks the leased inbox ``turn_committed`` in one SQLite transaction.
Every work-owning state has an expiring, generation-checked lease.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from hermes_constants import get_hermes_home

INBOX_SCHEMA_VERSION = 2
MAX_KEY_BYTES = 256
MAX_SCOPE_BYTES = 1024
MAX_PAYLOAD_BYTES = 1_048_576
_KEY_RE = re.compile(r"^[\x21-\x7e]{16,256}$")


class InjectionOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    ALREADY_ACCEPTED = "ALREADY_ACCEPTED"
    CONFLICT = "CONFLICT"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class InboxReceipt:
    outcome: InjectionOutcome
    inbox_id: Optional[str] = None


@dataclass(frozen=True)
class InboxRecord:
    inbox_id: str
    idempotency_key: str
    source_id: str
    session_key: str
    generation: str
    role: str
    payload: str
    attempts: int
    lease_generation: int


@dataclass(frozen=True)
class GatewayTurn:
    turn_id: str
    inbox_id: str
    source_id: str
    session_key: str
    session_id: str
    generation: str
    payload: str
    payload_digest: str
    attempts: int
    lease_generation: int
    state: str


_SCHEMA = """
CREATE TABLE IF NOT EXISTS gateway_inbox_schema(version INTEGER NOT NULL);
INSERT INTO gateway_inbox_schema(version)
SELECT 2 WHERE NOT EXISTS (SELECT 1 FROM gateway_inbox_schema);
CREATE TABLE IF NOT EXISTS gateway_inbox (
 idempotency_key TEXT PRIMARY KEY,
 inbox_id TEXT NOT NULL UNIQUE,
 profile_digest TEXT NOT NULL,
 source_id TEXT NOT NULL,
 session_key TEXT NOT NULL,
 generation TEXT NOT NULL,
 role TEXT NOT NULL,
 payload_digest TEXT NOT NULL,
 payload TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','leased','turn_committed','terminal','quarantined')),
 accepted_at REAL NOT NULL,
 retain_until REAL NOT NULL,
 lease_owner TEXT,
 lease_expires REAL,
 lease_generation INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0,
 turn_id TEXT UNIQUE,
 terminal_at REAL,
 outcome TEXT
);
CREATE INDEX IF NOT EXISTS gateway_inbox_drain ON gateway_inbox(state, lease_expires, accepted_at);
CREATE TABLE IF NOT EXISTS gateway_turns (
 turn_id TEXT PRIMARY KEY,
 inbox_id TEXT NOT NULL UNIQUE REFERENCES gateway_inbox(inbox_id),
 profile_digest TEXT NOT NULL,
 source_id TEXT NOT NULL,
 session_key TEXT NOT NULL,
 session_id TEXT NOT NULL,
 generation TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role='user'),
 payload_digest TEXT NOT NULL,
 payload TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','leased','user_committed','processing','completed','failed','quarantined')),
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 lease_owner TEXT,
 lease_expires REAL,
 lease_generation INTEGER NOT NULL DEFAULT 0,
 attempts INTEGER NOT NULL DEFAULT 0,
 user_message_id INTEGER,
 response_message_id INTEGER,
 outcome TEXT
);
CREATE INDEX IF NOT EXISTS gateway_turns_drain ON gateway_turns(state, lease_expires, created_at);
CREATE TABLE IF NOT EXISTS gateway_inbox_compaction_receipts(
 receipt_id TEXT PRIMARY KEY, compacted_at REAL NOT NULL, deleted_count INTEGER NOT NULL, cutoff REAL NOT NULL
);
"""


def _utf8(value: str, limit: int, *, opaque_key: bool = False) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError:
        return False
    if len(raw) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    return bool(_KEY_RE.fullmatch(value)) if opaque_key else True


class GatewayInbox:
    def __init__(self, db_path: Path | str | None = None, *, clock: Callable[[], float] = time.time):
        self.db_path = Path(db_path) if db_path is not None else get_hermes_home() / "state.db"
        self.clock = clock
        self.profile_digest = hashlib.sha256(os.fsencode(str(self.db_path.parent.resolve()))).hexdigest()
        self._migrate()

    def _connect(self, timeout: float = 5.0) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=timeout, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _migrate(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            old = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gateway_inbox'").fetchone()
            rebuild = False
            if old:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(gateway_inbox)")}
                sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='gateway_inbox'").fetchone()[0]
                rebuild = "turn_committed" not in sql or "lease_generation" not in cols
            legacy_sql = ""
            if rebuild:
                legacy_sql = """
                    ALTER TABLE gateway_inbox RENAME TO gateway_inbox_v1;
                """
            copy_sql = ""
            if rebuild:
                copy_sql = """INSERT OR IGNORE INTO gateway_inbox
                    (idempotency_key,inbox_id,profile_digest,source_id,session_key,generation,role,payload_digest,payload,
                     state,accepted_at,retain_until,attempts,turn_id,terminal_at,outcome)
                    SELECT idempotency_key,inbox_id,profile_digest,source_id,session_key,generation,role,payload_digest,payload,
                     CASE WHEN state='consumed' THEN 'terminal' WHEN state='turn_owned' THEN 'pending'
                          WHEN state='quarantined' THEN 'quarantined' ELSE 'pending' END,
                     accepted_at,retain_until,attempts,turn_id,consumed_at,outcome FROM gateway_inbox_v1;
                    DROP TABLE gateway_inbox_v1;
                    DROP INDEX IF EXISTS gateway_inbox_drain;
                    CREATE INDEX gateway_inbox_drain ON gateway_inbox(state, lease_expires, accepted_at);
                """
            # executescript commits before executing, so BEGIN must be part of
            # the script.  The rebuild, data copy, indexes, and version marker
            # are thereby one rollback-safe migration.
            conn.executescript(
                "BEGIN IMMEDIATE;\n" + legacy_sql + _SCHEMA + copy_sql
                + f"UPDATE gateway_inbox_schema SET version={INBOX_SCHEMA_VERSION};\nCOMMIT;"
            )
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def accept(self, *, idempotency_key: str, source_id: str, session_key: str,
               generation: str, role: str, payload: str, retain_seconds: int = 2_592_000) -> InboxReceipt:
        fields = (source_id, session_key, generation)
        try:
            payload_raw = payload.encode("utf-8", "strict") if isinstance(payload, str) else b""
        except UnicodeError:
            payload_raw = b""
        if (not _utf8(idempotency_key, MAX_KEY_BYTES, opaque_key=True)
                or any(not _utf8(v, MAX_SCOPE_BYTES) for v in fields)
                or role != "user" or not isinstance(payload, str) or not payload_raw
                or len(payload_raw) > MAX_PAYLOAD_BYTES or retain_seconds < 86_400):
            return InboxReceipt(InjectionOutcome.REJECTED)
        digest = hashlib.sha256(payload_raw).hexdigest()
        binding = (self.profile_digest, source_id, session_key, generation, role, digest)
        now, inbox_id = self.clock(), uuid.uuid4().hex
        try:
            conn = self._connect(timeout=0.1)
            try:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute("SELECT * FROM gateway_inbox WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                if row is not None:
                    actual = tuple(row[k] for k in ("profile_digest","source_id","session_key","generation","role","payload_digest"))
                    conn.rollback()
                    return InboxReceipt(InjectionOutcome.ALREADY_ACCEPTED if actual == binding else InjectionOutcome.CONFLICT, row["inbox_id"])
                conn.execute("""INSERT INTO gateway_inbox
                    (idempotency_key,inbox_id,profile_digest,source_id,session_key,generation,role,payload_digest,payload,state,accepted_at,retain_until)
                    VALUES(?,?,?,?,?,?,?,?,?,'pending',?,?)""", (idempotency_key,inbox_id,*binding[:-1],digest,payload,now,now+retain_seconds))
                conn.commit()
                return InboxReceipt(InjectionOutcome.ACCEPTED, inbox_id)
            except BaseException:
                if conn.in_transaction: conn.rollback()
                raise
            finally: conn.close()
        except sqlite3.OperationalError:
            return InboxReceipt(InjectionOutcome.RETRYABLE_FAILURE)
        except (sqlite3.DatabaseError, OSError):
            return InboxReceipt(InjectionOutcome.REJECTED)

    def lease_next(self, owner: str, *, lease_seconds: int = 60) -> Optional[InboxRecord]:
        if not _utf8(owner, MAX_SCOPE_BYTES): return None
        now = self.clock(); conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT * FROM gateway_inbox WHERE state='pending'
                OR (state='leased' AND lease_expires<=?) ORDER BY accepted_at LIMIT 1""", (now,)).fetchone()
            if row is None: conn.rollback(); return None
            generation = row["lease_generation"] + 1
            cur = conn.execute("""UPDATE gateway_inbox SET state='leased',lease_owner=?,lease_expires=?,
                lease_generation=?,attempts=attempts+1 WHERE inbox_id=? AND lease_generation=?""",
                (owner,now+lease_seconds,generation,row["inbox_id"],row["lease_generation"]))
            if cur.rowcount != 1: conn.rollback(); return None
            conn.commit()
            return InboxRecord(row["inbox_id"],row["idempotency_key"],row["source_id"],row["session_key"],
                row["generation"],row["role"],row["payload"],row["attempts"]+1,generation)
        finally: conn.close()

    def commit_turn(self, record: InboxRecord, owner: str) -> Optional[str]:
        """Atomically hand a leased inbox row to the durable turn queue."""
        conn = self._connect(); now = self.clock()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM gateway_inbox WHERE inbox_id=?", (record.inbox_id,)).fetchone()
            if row is None: conn.rollback(); return None
            if row["state"] == "turn_committed": conn.rollback(); return row["turn_id"]
            if (row["state"] != "leased" or row["lease_owner"] != owner
                    or row["lease_generation"] != record.lease_generation or row["lease_expires"] <= now):
                conn.rollback(); return None
            turn_id = row["turn_id"] or uuid.uuid4().hex
            conn.execute("""INSERT INTO gateway_turns
                (turn_id,inbox_id,profile_digest,source_id,session_key,session_id,generation,role,payload_digest,payload,state,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,'pending',?,?)""",
                (turn_id,row["inbox_id"],row["profile_digest"],row["source_id"],row["session_key"],row["generation"],
                 row["generation"],row["role"],row["payload_digest"],row["payload"],now,now))
            conn.execute("""UPDATE gateway_inbox SET state='turn_committed',turn_id=?,lease_owner=NULL,lease_expires=NULL
                WHERE inbox_id=?""", (turn_id,row["inbox_id"]))
            conn.commit(); return turn_id
        except BaseException:
            if conn.in_transaction: conn.rollback()
            raise
        finally: conn.close()

    # Compatibility name; unlike v1 it never creates a non-reclaimable state.
    def claim_turn(self, inbox_id: str, owner: str) -> Optional[str]:
        conn = self._connect()
        try: row = conn.execute("SELECT * FROM gateway_inbox WHERE inbox_id=?", (inbox_id,)).fetchone()
        finally: conn.close()
        if row is None: return None
        record = InboxRecord(row["inbox_id"],row["idempotency_key"],row["source_id"],row["session_key"],
            row["generation"],row["role"],row["payload"],row["attempts"],row["lease_generation"])
        return self.commit_turn(record, owner)

    def lease_turn(self, owner: str, *, turn_id: str | None = None,
                   lease_seconds: int = 60) -> Optional[GatewayTurn]:
        now=self.clock(); conn=self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row=conn.execute("""SELECT * FROM gateway_turns
              WHERE (? IS NULL OR turn_id=?) AND (state IN ('pending','user_committed')
              OR (state IN ('leased','processing') AND lease_expires<=?))
              ORDER BY created_at LIMIT 1""",(turn_id,turn_id,now)).fetchone()
            if row is None: conn.rollback(); return None
            gen=row["lease_generation"]+1
            target="processing" if row["user_message_id"] else "leased"
            conn.execute("UPDATE gateway_turns SET state=?,lease_owner=?,lease_expires=?,lease_generation=?,attempts=attempts+1,updated_at=? WHERE turn_id=?",
                (target,owner,now+lease_seconds,gen,now,row["turn_id"]))
            conn.commit()
            return GatewayTurn(row["turn_id"],row["inbox_id"],row["source_id"],row["session_key"],row["session_id"],row["generation"],
                row["payload"],row["payload_digest"],row["attempts"]+1,gen,target)
        finally: conn.close()

    def commit_user(self, turn: GatewayTurn, owner: str) -> Optional[int]:
        """Persist the canonical user row before adapter/background scheduling."""
        conn=self._connect(); now=self.clock()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row=conn.execute("SELECT * FROM gateway_turns WHERE turn_id=?",(turn.turn_id,)).fetchone()
            if row is None: conn.rollback(); return None
            if row["user_message_id"]: conn.rollback(); return row["user_message_id"]
            if row["lease_owner"]!=owner or row["lease_generation"]!=turn.lease_generation or row["lease_expires"]<=now:
                conn.rollback(); return None
            session=conn.execute("SELECT id,session_key FROM sessions WHERE id=?",(row["session_id"],)).fetchone()
            if session is None or session["session_key"] != row["session_key"]:
                conn.execute("UPDATE gateway_turns SET state='quarantined',outcome='session_binding_mismatch',updated_at=? WHERE turn_id=?",(now,turn.turn_id))
                conn.commit(); return None
            cur=conn.execute("""INSERT INTO messages(session_id,role,content,timestamp,gateway_turn_id,gateway_turn_kind)
                VALUES(?,'user',?,?,?,'user')""",(row["session_id"],row["payload"],now,row["turn_id"]))
            message_id=cur.lastrowid
            conn.execute("UPDATE sessions SET message_count=message_count+1 WHERE id=?",(row["session_id"],))
            conn.execute("""UPDATE gateway_turns SET state='user_committed',user_message_id=?,lease_owner=NULL,
                lease_expires=NULL,updated_at=? WHERE turn_id=?""",(message_id,now,row["turn_id"]))
            conn.commit(); return message_id
        except sqlite3.IntegrityError:
            if conn.in_transaction: conn.rollback()
            row=conn.execute("SELECT id,content FROM messages WHERE gateway_turn_id=? AND gateway_turn_kind='user'",(turn.turn_id,)).fetchone()
            return row["id"] if row and hashlib.sha256((row["content"] or "").encode()).hexdigest()==turn.payload_digest else None
        finally: conn.close()

    def complete_response(self, turn_id: str, content: str, *, outcome: str="completed") -> Optional[int]:
        """Idempotently bind one final assistant response to a durable turn."""
        conn=self._connect(); now=self.clock()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row=conn.execute("SELECT * FROM gateway_turns WHERE turn_id=?",(turn_id,)).fetchone()
            if row is None or not row["user_message_id"]: conn.rollback(); return None
            if row["response_message_id"]: conn.rollback(); return row["response_message_id"]
            cur=conn.execute("""INSERT INTO messages(session_id,role,content,timestamp,gateway_turn_id,gateway_turn_kind)
                VALUES(?,'assistant',?,?,?,'response')""",(row["session_id"],content,now,turn_id))
            mid=cur.lastrowid
            conn.execute("UPDATE sessions SET message_count=message_count+1 WHERE id=?",(row["session_id"],))
            conn.execute("UPDATE gateway_turns SET state='completed',response_message_id=?,outcome=?,lease_owner=NULL,lease_expires=NULL,updated_at=? WHERE turn_id=?",
                (mid,outcome[:128],now,turn_id))
            conn.execute("UPDATE gateway_inbox SET state='terminal',terminal_at=?,outcome=? WHERE inbox_id=?",(now,outcome[:128],row["inbox_id"]))
            conn.commit(); return mid
        except sqlite3.IntegrityError:
            if conn.in_transaction: conn.rollback()
            existing=conn.execute("SELECT id,content FROM messages WHERE gateway_turn_id=? AND gateway_turn_kind='response'",(turn_id,)).fetchone()
            return existing["id"] if existing and existing["content"]==content else None
        finally: conn.close()

    def finish(self, inbox_id: str, turn_id: str, outcome: str) -> bool:
        """Compatibility: only terminalize after a durable response exists."""
        conn=self._connect()
        try:
            row=conn.execute("SELECT state FROM gateway_turns WHERE turn_id=? AND inbox_id=?",(turn_id,inbox_id)).fetchone()
            return bool(row and row["state"] in ("completed","failed","quarantined"))
        finally: conn.close()

    def compact(self, *, limit: int = 500) -> tuple[str, int]:
        now=self.clock(); receipt=uuid.uuid4().hex; conn=self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows=conn.execute("SELECT inbox_id FROM gateway_inbox WHERE state='terminal' AND retain_until<=? LIMIT ?",(now,max(1,min(limit,5000)))).fetchall()
            for row in rows:
                conn.execute("DELETE FROM gateway_turns WHERE inbox_id=? AND state IN ('completed','failed','quarantined')",(row[0],))
                conn.execute("DELETE FROM gateway_inbox WHERE inbox_id=? AND state='terminal'",(row[0],))
            conn.execute("INSERT INTO gateway_inbox_compaction_receipts VALUES(?,?,?,?)",(receipt,now,len(rows),now))
            conn.commit(); return receipt,len(rows)
        except BaseException:
            if conn.in_transaction: conn.rollback()
            raise
        finally: conn.close()
