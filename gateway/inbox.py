"""Durable, accepted-once gateway inbox.

The acceptance transaction is the public durability boundary.  Dispatch remains
at-least-once; ``claim_turn`` is the durable handoff that prevents a replay from
creating a second conversation turn for one inbox record.
"""
from __future__ import annotations

import hashlib
import json
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

INBOX_SCHEMA_VERSION = 1
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


_SCHEMA = """
CREATE TABLE IF NOT EXISTS gateway_inbox_schema(version INTEGER NOT NULL);
INSERT INTO gateway_inbox_schema(version)
SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM gateway_inbox_schema);
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
 state TEXT NOT NULL CHECK(state IN ('pending','leased','turn_owned','consumed','quarantined')),
 accepted_at REAL NOT NULL,
 retain_until REAL NOT NULL,
 lease_owner TEXT,
 lease_expires REAL,
 attempts INTEGER NOT NULL DEFAULT 0,
 turn_id TEXT UNIQUE,
 consumed_at REAL,
 outcome TEXT
);
CREATE INDEX IF NOT EXISTS gateway_inbox_drain ON gateway_inbox(state, lease_expires, accepted_at);
CREATE TABLE IF NOT EXISTS gateway_inbox_compaction_receipts(
 receipt_id TEXT PRIMARY KEY, compacted_at REAL NOT NULL, deleted_count INTEGER NOT NULL,
 cutoff REAL NOT NULL
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
    """SQLite inbox sharing the canonical profile ``state.db``."""

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
            # executescript otherwise commits any transaction opened by the
            # caller.  Put BEGIN/COMMIT inside the script so every additive DDL
            # statement and the version marker are one atomic migration.
            conn.executescript("BEGIN IMMEDIATE;\n" + _SCHEMA + "\nCOMMIT;")
            row = conn.execute("SELECT version FROM gateway_inbox_schema LIMIT 1").fetchone()
            if row is None or row[0] != INBOX_SCHEMA_VERSION:
                raise sqlite3.DatabaseError("unsupported gateway inbox schema")
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    def accept(self, *, idempotency_key: str, source_id: str, session_key: str,
               generation: str, role: str, payload: str, retain_seconds: int = 2_592_000) -> InboxReceipt:
        fields = (source_id, session_key, generation)
        if (not _utf8(idempotency_key, MAX_KEY_BYTES, opaque_key=True)
                or any(not _utf8(v, MAX_SCOPE_BYTES) for v in fields)
                or role != "user" or not isinstance(payload, str)
                or len(payload.encode("utf-8", "strict")) > MAX_PAYLOAD_BYTES
                or retain_seconds < 86_400):
            return InboxReceipt(InjectionOutcome.REJECTED)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        binding = (self.profile_digest, source_id, session_key, generation, role, digest)
        now = self.clock()
        inbox_id = uuid.uuid4().hex
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
                    (idempotency_key,inbox_id,profile_digest,source_id,session_key,generation,role,
                     payload_digest,payload,state,accepted_at,retain_until)
                    VALUES(?,?,?,?,?,?,?,?,?,'pending',?,?)""",
                    (idempotency_key,inbox_id,*binding[:-1],digest,payload,now,now+retain_seconds))
                conn.commit()
                return InboxReceipt(InjectionOutcome.ACCEPTED, inbox_id)
            except BaseException:
                conn.rollback()
                raise
            finally:
                conn.close()
        except sqlite3.OperationalError:
            return InboxReceipt(InjectionOutcome.RETRYABLE_FAILURE)
        except (sqlite3.DatabaseError, OSError, UnicodeError):
            return InboxReceipt(InjectionOutcome.REJECTED)

    def lease_next(self, owner: str, *, lease_seconds: int = 60) -> Optional[InboxRecord]:
        if not _utf8(owner, MAX_SCOPE_BYTES):
            return None
        now = self.clock()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""SELECT * FROM gateway_inbox
                WHERE state='pending' OR (state='leased' AND lease_expires<=?)
                ORDER BY accepted_at LIMIT 1""", (now,)).fetchone()
            if row is None:
                conn.rollback(); return None
            conn.execute("""UPDATE gateway_inbox SET state='leased', lease_owner=?, lease_expires=?,
                attempts=attempts+1 WHERE inbox_id=?""", (owner, now+lease_seconds, row["inbox_id"]))
            conn.commit()
            return InboxRecord(row["inbox_id"], row["idempotency_key"], row["source_id"],
                               row["session_key"], row["generation"], row["role"], row["payload"], row["attempts"]+1)
        finally:
            conn.close()

    def claim_turn(self, inbox_id: str, owner: str) -> Optional[str]:
        """Durably create exactly one turn identity for an owned lease."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT state,lease_owner,turn_id FROM gateway_inbox WHERE inbox_id=?", (inbox_id,)).fetchone()
            if row is None or row["lease_owner"] != owner:
                conn.rollback(); return None
            if row["turn_id"]:
                conn.rollback(); return row["turn_id"]
            turn_id = uuid.uuid4().hex
            conn.execute("UPDATE gateway_inbox SET state='turn_owned',turn_id=? WHERE inbox_id=?", (turn_id,inbox_id))
            conn.commit(); return turn_id
        finally:
            conn.close()

    def finish(self, inbox_id: str, turn_id: str, outcome: str) -> bool:
        conn = self._connect()
        try:
            cur = conn.execute("""UPDATE gateway_inbox SET state='consumed',consumed_at=?,outcome=?,
                lease_owner=NULL,lease_expires=NULL WHERE inbox_id=? AND turn_id=? AND state='turn_owned'""",
                (self.clock(), outcome[:128], inbox_id, turn_id))
            return cur.rowcount == 1
        finally:
            conn.close()

    def compact(self, *, limit: int = 500) -> tuple[str, int]:
        now = self.clock(); receipt = uuid.uuid4().hex
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute("SELECT idempotency_key FROM gateway_inbox WHERE state='consumed' AND retain_until<=? LIMIT ?", (now,max(1,min(limit,5000)))).fetchall()
            if rows:
                conn.executemany("DELETE FROM gateway_inbox WHERE idempotency_key=? AND state='consumed'", [(r[0],) for r in rows])
            conn.execute("INSERT INTO gateway_inbox_compaction_receipts VALUES(?,?,?,?)", (receipt,now,len(rows),now))
            conn.commit(); return receipt,len(rows)
        except BaseException:
            conn.rollback(); raise
        finally:
            conn.close()
