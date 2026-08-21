"""Durable, non-conversational session notifications.

Notifications are metadata records.  This module deliberately has no dependency on
the gateway runner, adapters, model loop, tools, prompts, or transcript APIs.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping


MAX_TEXT_BYTES = 256
MAX_METADATA_BYTES = 2048
MAX_ACK_RETENTION_SECONDS = 90 * 86400
MIGRATION_MARKER = "session_notifications_legacy_migrated_v2"
_ALLOWED_METADATA = {
    "event": str,
    "sender": str,
    "device": str,
    "sha256": str,
    "bytes": int,
    "generation": int,
    "status_label": str,
}


class NotificationOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    ALREADY_ACCEPTED = "ALREADY_ACCEPTED"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"


@dataclass(frozen=True)
class NotificationReceipt:
    outcome: NotificationOutcome
    notification_id: str | None = None
    digest: str | None = None


@dataclass(frozen=True)
class SessionNotification:
    notification_id: str
    idempotency_key: str
    profile_name: str
    plugin_id: str
    session_id: str
    session_key: str
    destination: str
    generation: int
    metadata: dict[str, Any]
    metadata_digest: str
    status: str
    created_at: float
    acknowledged_at: float | None
    retain_until: float | None


@dataclass(frozen=True)
class OwnerNotificationContext:
    """Opaque capability minted only by an authenticated gateway boundary."""

    platform: str
    user_id: str
    chat_id: str
    profile_name: str
    session_key: str
    generation: int
    _issuer: object


class GatewayNotificationOwnerBoundary:
    """Owner read/ack facade which revalidates live gateway auth on every call."""

    def __init__(self, store: "SessionNotificationStore", *, captain_user_id: str,
                 platform: str, chat_id: str, profile_name: str, session_key: str,
                 generation: int, authorization_check: Callable[[str, str, str], bool]):
        self._store = store
        self._captain = _bounded_text(captain_user_id, name="captain_user_id")
        self._binding = (platform, chat_id, profile_name, session_key, generation)
        self._authorization_check = authorization_check
        self._issuer = object()

    def issue(self, *, user_id: str, platform: str, chat_id: str,
              profile_name: str, session_key: str, generation: int) -> OwnerNotificationContext | None:
        supplied = (platform, chat_id, profile_name, session_key, generation)
        if user_id != self._captain or supplied != self._binding:
            return None
        if not self._authorization_check(user_id, platform, chat_id):
            return None
        return OwnerNotificationContext(platform, user_id, chat_id, profile_name,
                                        session_key, generation, self._issuer)

    def _validate(self, context: OwnerNotificationContext) -> bool:
        return (
            type(context) is OwnerNotificationContext
            and context._issuer is self._issuer
            and context.user_id == self._captain
            and (context.platform, context.chat_id, context.profile_name,
                 context.session_key, context.generation) == self._binding
            and self._authorization_check(context.user_id, context.platform, context.chat_id)
        )

    def list_pending(self, context: OwnerNotificationContext, *, plugin_id: str,
                     limit: int = 100) -> list[SessionNotification]:
        if not self._validate(context):
            return []
        return self._store._list_pending(profile_name=context.profile_name, plugin_id=plugin_id,
                                         session_key=context.session_key, limit=limit)

    def fetch(self, context: OwnerNotificationContext, notification_id: str,
              *, plugin_id: str) -> SessionNotification | None:
        if not self._validate(context):
            return None
        return self._store._fetch(notification_id, profile_name=context.profile_name,
                                  plugin_id=plugin_id, session_key=context.session_key)

    def acknowledge(self, context: OwnerNotificationContext, notification_id: str,
                    *, plugin_id: str, retention_seconds: int = 30 * 86400) -> bool:
        if not self._validate(context):
            return False
        binding = json.dumps({"platform": context.platform, "user_id": context.user_id,
                              "chat_id": context.chat_id, "generation": context.generation},
                             sort_keys=True, separators=(",", ":"))
        return self._store._acknowledge(
            notification_id, profile_name=context.profile_name, plugin_id=plugin_id,
            session_key=context.session_key, generation=context.generation,
            identity_binding=binding, retention_seconds=retention_seconds,
        )


def _bounded_text(value: Any, *, name: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise ValueError(f"{name} must be a non-empty string")
    if "\x00" in value or "\n" in value or len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError(f"invalid {name}")
    return value


def canonicalize_metadata(metadata: Mapping[str, Any], generation: int) -> tuple[str, str]:
    if not isinstance(metadata, Mapping) or set(metadata) - _ALLOWED_METADATA.keys():
        raise ValueError("notification metadata contains unknown fields")
    if not metadata.get("event"):
        raise ValueError("notification metadata requires event")
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        expected = _ALLOWED_METADATA[key]
        if type(value) is not expected:  # bool is intentionally not an int here
            raise ValueError(f"invalid metadata field {key}")
        if expected is str:
            clean[key] = _bounded_text(value, name=key)
        elif value < 0:
            raise ValueError(f"invalid metadata field {key}")
        else:
            clean[key] = value
    if "generation" in clean and clean["generation"] != generation:
        raise ValueError("metadata generation does not match binding")
    digest_value = clean.get("sha256")
    if digest_value is not None and (
        len(digest_value) != 64 or any(c not in "0123456789abcdef" for c in digest_value)
    ):
        raise ValueError("sha256 must be 64 lowercase hex characters")
    payload = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(payload.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError("notification metadata is too large")
    return payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SessionNotificationStore:
    """Atomic notification ledger backed by the canonical state database."""

    def __init__(self, db_path: Path, *, clock=time.time, timeout: float = 5.0):
        self.db_path = Path(db_path)
        self.clock = clock
        self.timeout = timeout

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def migrate_legacy_gateway_notifications(self) -> int:
        """Preserve ambiguous pre-ledger candidates as quarantined metadata.

        Legacy rows remain untouched as evidence.  No transcript row is read,
        changed, or deleted.  The marker is committed in the same transaction,
        so a crash or busy database safely retries the entire migration.
        """
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute("SELECT 1 FROM state_meta WHERE key=?", (MIGRATION_MARKER,)).fetchone():
                conn.rollback()
                return 0
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            represented = 0
            rows = []
            if {"gateway_turns", "gateway_inbox"} <= tables:
                rows = conn.execute(
                    "SELECT t.turn_id,t.inbox_id,t.source_id,t.session_key,t.session_id,"
                    "t.generation,t.created_at,i.idempotency_key "
                    "FROM gateway_turns t JOIN gateway_inbox i ON i.inbox_id=t.inbox_id "
                    "ORDER BY t.turn_id,t.inbox_id"
                ).fetchall()
                for row in rows:
                    metadata_json, digest = canonicalize_metadata(
                        {"event": "legacy_gateway_notification", "generation": max(0, int(row["generation"])),
                         "status_label": "ambiguous_quarantined"},
                        max(0, int(row["generation"])),
                    )
                    key = "legacy:" + hashlib.sha256(
                        str(row["idempotency_key"]).encode("utf-8")
                    ).hexdigest()
                    identity = hashlib.sha256(json.dumps(
                        [str(row["turn_id"]), str(row["inbox_id"])],
                        separators=(",", ":"),
                    ).encode()).hexdigest()
                    by_key = conn.execute(
                        "SELECT * FROM session_notifications WHERE idempotency_key=?", (key,)
                    ).fetchone()
                    by_id = conn.execute(
                        "SELECT * FROM session_notifications WHERE notification_id=?",
                        (str(row["turn_id"]),),
                    ).fetchone()
                    existing = by_key or by_id
                    expected = (key, str(row["turn_id"]), "legacy-unknown", str(row["source_id"]),
                                str(row["session_id"]), str(row["session_key"]),
                                str(row["session_key"]), max(0, int(row["generation"])), digest)
                    if existing is not None:
                        actual = tuple(existing[name] for name in (
                            "idempotency_key", "notification_id", "profile_name", "plugin_id",
                            "session_id", "session_key", "destination", "generation", "metadata_digest",
                        ))
                        if actual != expected:
                            conflict_class = "key_and_id" if by_key and by_id else (
                                "idempotency_key" if by_key else "notification_id"
                            )
                            now = self.clock()
                            prior = conn.execute(
                                "SELECT metadata_digest,conflict_class FROM "
                                "session_notification_migration_conflicts WHERE "
                                "source_table='gateway_turns' AND source_identity=?", (identity,)
                            ).fetchone()
                            if prior is not None and tuple(prior) != (digest, conflict_class):
                                raise sqlite3.IntegrityError("legacy conflict receipt changed")
                            if prior is None:
                                conn.execute(
                                    "INSERT INTO session_notification_migration_conflicts "
                                    "(source_table,source_identity,metadata_digest,conflict_class,"
                                    "first_seen_at,last_seen_at) VALUES('gateway_turns',?,?,?,?,?)",
                                    (identity, digest, conflict_class, now, now),
                                )
                    else:
                        conn.execute(
                            "INSERT INTO session_notifications "
                            "(idempotency_key,notification_id,profile_name,plugin_id,session_id,"
                            "session_key,destination,generation,metadata_json,metadata_digest,status,"
                            "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,'quarantined',?,?)",
                            (key, str(row["turn_id"]), "legacy-unknown", str(row["source_id"]),
                             str(row["session_id"]), str(row["session_key"]), str(row["session_key"]),
                             max(0, int(row["generation"])), metadata_json, digest,
                             float(row["created_at"]), self.clock()),
                        )
                    represented += 1
            if represented != len(rows):
                raise sqlite3.IntegrityError("legacy notification migration count mismatch")
            receipt = json.dumps({
                "version": 2, "source_count": len(rows), "represented_count": represented,
                "source_digest": hashlib.sha256("\n".join(
                    f'{row["turn_id"]}:{row["inbox_id"]}' for row in rows
                ).encode()).hexdigest(),
            }, sort_keys=True, separators=(",", ":"))
            conn.execute("INSERT INTO state_meta(key,value) VALUES(?,?)", (MIGRATION_MARKER, receipt))
            conn.commit()
            return represented
        except BaseException:
            if conn.in_transaction:
                conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> SessionNotification:
        return SessionNotification(
            notification_id=row["notification_id"],
            idempotency_key=row["idempotency_key"],
            profile_name=row["profile_name"],
            plugin_id=row["plugin_id"],
            session_id=row["session_id"],
            session_key=row["session_key"],
            destination=row["destination"],
            generation=row["generation"],
            metadata=json.loads(row["metadata_json"]),
            metadata_digest=row["metadata_digest"],
            status=row["status"],
            created_at=row["created_at"],
            acknowledged_at=row["acknowledged_at"],
            retain_until=row["retain_until"],
        )

    def append_once(self, *, idempotency_key: str, profile_name: str, plugin_id: str,
                    session_key: str, destination: str, generation: int,
                    metadata: Mapping[str, Any]) -> NotificationReceipt:
        try:
            key = _bounded_text(idempotency_key, name="idempotency_key")
            profile = _bounded_text(profile_name, name="profile_name")
            plugin = _bounded_text(plugin_id, name="plugin_id")
            session_key = _bounded_text(session_key, name="session_key")
            destination = _bounded_text(destination, name="destination")
            if type(generation) is not int or generation < 0:
                raise ValueError("generation must be a non-negative integer")
            payload, digest = canonicalize_metadata(metadata, generation)
        except ValueError:
            return NotificationReceipt(NotificationOutcome.REJECTED)

        binding = (profile, plugin, session_key, destination, generation, digest)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM session_notifications WHERE idempotency_key=?", (key,)
            ).fetchone()
            if existing is not None:
                exact = tuple(existing[name] for name in (
                    "profile_name", "plugin_id", "session_key", "destination",
                    "generation", "metadata_digest",
                )) == binding
                conn.rollback()
                return NotificationReceipt(
                    NotificationOutcome.ALREADY_ACCEPTED if exact else NotificationOutcome.CONFLICT,
                    existing["notification_id"], existing["metadata_digest"],
                )
            session = conn.execute(
                "SELECT id FROM sessions WHERE session_key=? AND "
                "COALESCE(profile_name, ?)=? ORDER BY started_at DESC LIMIT 1",
                (session_key, profile, profile),
            ).fetchone()
            if session is None:
                conn.rollback()
                return NotificationReceipt(NotificationOutcome.REJECTED)
            notification_id = uuid.uuid4().hex
            now = self.clock()
            conn.execute(
                "INSERT INTO session_notifications "
                "(idempotency_key,notification_id,profile_name,plugin_id,session_id,"
                "session_key,destination,generation,metadata_json,metadata_digest,status,"
                "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,'pending',?,?)",
                (key, notification_id, profile, plugin, session["id"], session_key,
                 destination, generation, payload, digest, now, now),
            )
            conn.commit()
            return NotificationReceipt(NotificationOutcome.ACCEPTED, notification_id, digest)
        except sqlite3.OperationalError:
            if conn.in_transaction:
                conn.rollback()
            return NotificationReceipt(NotificationOutcome.RETRYABLE_FAILURE)
        finally:
            conn.close()

    def _list_pending(self, *, profile_name: str, plugin_id: str,
                     session_key: str, limit: int = 100) -> list[SessionNotification]:
        profile = _bounded_text(profile_name, name="profile_name")
        plugin = _bounded_text(plugin_id, name="plugin_id")
        session_key = _bounded_text(session_key, name="session_key")
        limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM session_notifications WHERE profile_name=? AND plugin_id=? "
                "AND session_key=? AND status='pending' ORDER BY created_at,notification_id LIMIT ?",
                (profile, plugin, session_key, limit),
            ).fetchall()
        return [self._record(row) for row in rows]

    def _fetch(self, notification_id: str, *, profile_name: str, plugin_id: str,
              session_key: str) -> SessionNotification | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM session_notifications WHERE notification_id=? AND "
                "profile_name=? AND plugin_id=? AND session_key=?",
                (notification_id, profile_name, plugin_id, session_key),
            ).fetchone()
        return self._record(row) if row else None

    def _acknowledge(self, notification_id: str, *, profile_name: str, plugin_id: str,
                    session_key: str, generation: int, identity_binding: str,
                    retention_seconds: int = 30 * 86400) -> bool:
        identity_binding = _bounded_text(identity_binding, name="identity_binding")
        identity_digest = hashlib.sha256(identity_binding.encode()).hexdigest()
        retention = max(0, min(int(retention_seconds), MAX_ACK_RETENTION_SECONDS))
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM session_notifications WHERE notification_id=? AND "
                "profile_name=? AND plugin_id=? AND session_key=? AND generation=?",
                (notification_id, profile_name, plugin_id, session_key, generation),
            ).fetchone()
            if row is None:
                conn.rollback()
                return False
            if row["status"] == "acknowledged":
                conn.rollback()
                return row["acknowledged_by"] == identity_digest
            if row["status"] != "pending":
                conn.rollback()
                return False
            now = self.clock()
            conn.execute(
                "UPDATE session_notifications SET status='acknowledged',acknowledged_at=?,"
                "acknowledged_by=?,retain_until=?,updated_at=? WHERE notification_id=?",
                (now, identity_digest, now + retention, now, notification_id),
            )
            conn.execute(
                "INSERT INTO session_notification_owner_audit "
                "(audit_id,notification_id,action,identity_binding,identity_digest,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (uuid.uuid4().hex, notification_id, "acknowledge", identity_binding,
                 identity_digest, now),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def compact_acknowledged(self, *, limit: int = 500) -> tuple[str, int]:
        receipt = uuid.uuid4().hex
        now = self.clock()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT notification_id FROM session_notifications WHERE status='acknowledged' "
                "AND retain_until IS NOT NULL AND retain_until<=? LIMIT ?", (now, max(1, min(limit, 5000)))
            ).fetchall()
            conn.execute(
                "INSERT INTO session_notification_compaction_receipts(receipt_id,created_at,row_count) "
                "VALUES(?,?,?)", (receipt, now, len(rows)),
            )
            if rows:
                conn.executemany(
                    "DELETE FROM session_notifications WHERE notification_id=? AND status='acknowledged'",
                    [(row[0],) for row in rows],
                )
            conn.commit()
            return receipt, len(rows)
        finally:
            conn.close()
