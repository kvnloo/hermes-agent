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
MIGRATION_VERSION = 4
MIGRATION_MARKER = "session_notifications_legacy_migrated_v4"
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

    def __init__(self, db_path: Path, *, clock=time.time, timeout: float = 5.0,
                 failure_hook: Callable[[str], None] | None = None):
        self.db_path = Path(db_path)
        self.clock = clock
        self.timeout = timeout
        self._failure_hook = failure_hook

    def _failpoint(self, name: str) -> None:
        if self._failure_hook is not None:
            self._failure_hook(name)

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
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            rows = []
            if {"gateway_turns", "gateway_inbox"} <= tables:
                rows = conn.execute(
                    "SELECT t.turn_id,t.inbox_id,t.source_id,t.session_key,t.session_id,"
                    "t.generation,t.created_at,i.idempotency_key "
                    "FROM gateway_turns t JOIN gateway_inbox i ON i.inbox_id=t.inbox_id "
                    "ORDER BY t.turn_id,t.inbox_id"
                ).fetchall()

            source_digests: list[str] = []
            classes: list[tuple[str, str, str, str | None, str | None]] = []
            for row in rows:
                generation = max(0, int(row["generation"]))
                metadata_json, metadata_digest = canonicalize_metadata(
                    {"event": "legacy_gateway_notification", "generation": generation,
                     "status_label": "ambiguous_quarantined"}, generation,
                )
                source_identity = hashlib.sha256(json.dumps(
                    ["gateway_turns", str(row["turn_id"]), str(row["inbox_id"])],
                    separators=(",", ":"), ensure_ascii=False,
                ).encode()).hexdigest()
                source_envelope = {
                    "source_table": "gateway_turns", "source_row_identity": source_identity,
                    "turn_id": str(row["turn_id"]), "inbox_id": str(row["inbox_id"]),
                    "legacy_idempotency_key": str(row["idempotency_key"]),
                    "notification_id": str(row["turn_id"]), "profile_name": "legacy-unknown",
                    "plugin_id": str(row["source_id"]), "session_id": str(row["session_id"]),
                    "session_key": str(row["session_key"]), "destination": str(row["session_key"]),
                    "generation": generation, "created_at": float(row["created_at"]),
                    "metadata_digest": metadata_digest,
                }
                source_digest = hashlib.sha256(json.dumps(
                    source_envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                ).encode()).hexdigest()
                source_digests.append(source_digest)
                prior = conn.execute(
                    "SELECT classification,source_digest,target_id,conflict_id FROM "
                    "session_notification_migration_classifications WHERE migration_version=? AND "
                    "source_table='gateway_turns' AND source_row_identity=?",
                    (MIGRATION_VERSION, source_identity),
                ).fetchone()
                if prior is not None:
                    if prior["source_digest"] != source_digest:
                        raise sqlite3.IntegrityError("legacy source digest changed")
                    if prior["classification"] in {"inserted", "represented_existing"}:
                        target = conn.execute(
                            "SELECT 1 FROM session_notifications WHERE notification_id=?",
                            (prior["target_id"],),
                        ).fetchone()
                        if target is None:
                            raise sqlite3.IntegrityError("classified notification is missing")
                    elif conn.execute(
                        "SELECT 1 FROM session_notification_migration_conflicts WHERE "
                        "source_table='gateway_turns' AND source_identity=?", (source_identity,),
                    ).fetchone() is None:
                        raise sqlite3.IntegrityError("classified migration conflict is missing")
                    classes.append((source_identity, prior["classification"], source_digest,
                                    prior["target_id"], prior["conflict_id"]))
                    continue
                key = "legacy:" + hashlib.sha256(
                    str(row["idempotency_key"]).encode("utf-8")
                ).hexdigest()
                expected = (key, str(row["turn_id"]), "legacy-unknown", str(row["source_id"]),
                            str(row["session_id"]), str(row["session_key"]),
                            str(row["session_key"]), generation, metadata_digest)
                # Only the schema's two globally unique identities can collide.
                # Binding and metadata values are deliberately non-unique: a
                # session may legitimately receive many identical notifications.
                collisions = conn.execute(
                    "SELECT * FROM session_notifications WHERE idempotency_key=? OR "
                    "notification_id=?",
                    (key, str(row["turn_id"])),
                ).fetchall()
                exact = next((candidate for candidate in collisions if tuple(candidate[name] for name in (
                    "idempotency_key", "notification_id", "profile_name", "plugin_id", "session_id",
                    "session_key", "destination", "generation", "metadata_digest")) == expected), None)
                target_id: str | None = None
                conflict_id: str | None = None
                if exact is not None:
                    classification = "represented_existing"
                    target_id = str(exact["notification_id"])
                elif collisions:
                    classification = "migration_conflict"
                    collision_kinds: list[str] = []
                    for candidate in collisions:
                        if candidate["idempotency_key"] == key: collision_kinds.append("key")
                        if candidate["notification_id"] == str(row["turn_id"]): collision_kinds.append("notification_id")
                    conflict_class = "+".join(sorted(set(collision_kinds)))
                    conflict_id = hashlib.sha256(
                        f"{MIGRATION_VERSION}:gateway_turns:{source_identity}:{conflict_class}".encode()
                    ).hexdigest()
                    self._failpoint("before_conflict_insert")
                    conn.execute(
                        "INSERT INTO session_notification_migration_conflicts "
                        "(source_table,source_identity,metadata_digest,conflict_class,first_seen_at,last_seen_at) "
                        "VALUES('gateway_turns',?,?,?,?,?) ON CONFLICT(source_table,source_identity) "
                        "DO UPDATE SET last_seen_at=excluded.last_seen_at",
                        (source_identity, source_digest, conflict_class, self.clock(), self.clock()),
                    )
                    self._failpoint("after_conflict_insert")
                else:
                    classification = "inserted"
                    target_id = str(row["turn_id"])
                    self._failpoint("before_notification_insert")
                    conn.execute(
                        "INSERT INTO session_notifications "
                        "(idempotency_key,notification_id,profile_name,plugin_id,session_id,session_key,"
                        "destination,generation,metadata_json,metadata_digest,status,created_at,updated_at) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,'quarantined',?,?)",
                        (*expected[:8], metadata_json, metadata_digest, float(row["created_at"]), self.clock()),
                    )
                    self._failpoint("after_notification_insert")

                    # A committed v3 receipt is immutable evidence.  Its false
                    # binding/digest conflict row, however, is not a v4 conflict
                    # and must not remain the current conflict projection.
                    conn.execute(
                        "DELETE FROM session_notification_migration_conflicts WHERE "
                        "source_table='gateway_turns' AND source_identity=? AND "
                        "conflict_class IN ('binding','digest','binding+digest')",
                        (source_identity,),
                    )

                receipt = (classification, source_digest, target_id, conflict_id)
                self._failpoint("before_classification_insert")
                conn.execute(
                    "INSERT INTO session_notification_migration_classifications VALUES(?,?,?,?,?,?,?,?)",
                    (MIGRATION_VERSION, "gateway_turns", source_identity, source_digest,
                     classification, target_id, conflict_id, self.clock()),
                )
                self._failpoint("after_classification_insert")
                classes.append((source_identity, classification, source_digest, target_id, conflict_id))

            class_counts = {name: sum(1 for item in classes if item[1] == name) for name in
                            ("inserted", "represented_existing", "migration_conflict")}
            if sum(class_counts.values()) != len(rows):
                raise sqlite3.IntegrityError("legacy notification migration count mismatch")
            class_digest = hashlib.sha256("\n".join(
                json.dumps(item, separators=(",", ":")) for item in sorted(classes)
            ).encode()).hexdigest()
            source_aggregate = hashlib.sha256("\n".join(sorted(source_digests)).encode()).hexdigest()
            receipt_obj = {"version": MIGRATION_VERSION, "source_count": len(rows),
                           **{f"{key}_count": value for key, value in class_counts.items()},
                           "classification_aggregate_digest": class_digest,
                           "source_aggregate_digest": source_aggregate}
            receipt = json.dumps(receipt_obj, sort_keys=True, separators=(",", ":"))
            marker = conn.execute("SELECT value FROM state_meta WHERE key=?", (MIGRATION_MARKER,)).fetchone()
            if marker is not None:
                if marker[0] != receipt:
                    raise sqlite3.IntegrityError("legacy migration marker changed")
                conn.rollback()
                return 0
            self._failpoint("before_marker")
            conn.execute("INSERT INTO state_meta(key,value) VALUES(?,?)", (MIGRATION_MARKER, receipt))
            self._failpoint("after_marker")
            self._failpoint("before_commit")
            conn.commit()
            self._failpoint("after_commit")
            return len(rows)
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
                     session_key: str, generation: int,
                     limit: int = 100) -> list[SessionNotification]:
        profile = _bounded_text(profile_name, name="profile_name")
        plugin = _bounded_text(plugin_id, name="plugin_id")
        session_key = _bounded_text(session_key, name="session_key")
        limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM session_notifications WHERE profile_name=? AND plugin_id=? "
                "AND session_key=? AND generation=? AND status='pending' "
                "ORDER BY created_at,notification_id LIMIT ?",
                (profile, plugin, session_key, generation, limit),
            ).fetchall()
        return [self._record(row) for row in rows]

    def _fetch(self, notification_id: str, *, profile_name: str, plugin_id: str,
              session_key: str, generation: int) -> SessionNotification | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM session_notifications WHERE notification_id=? AND "
                "profile_name=? AND plugin_id=? AND session_key=? AND generation=?",
                (notification_id, profile_name, plugin_id, session_key, generation),
            ).fetchone()
        return self._record(row) if row else None

    def _acknowledge(self, notification_id: str, *, profile_name: str, plugin_id: str,
                    session_key: str, generation: int, identity_binding: str,
                    retention_seconds: int = 30 * 86400,
                    still_authorized: Callable[[], bool] | None = None) -> bool:
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
                # Owner actions are single-use.  A copied/replayed command or
                # callback never receives a second successful resolution.
                return False
            if row["status"] != "pending":
                conn.rollback()
                return False
            if still_authorized is not None and not still_authorized():
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
            self._failpoint("before_compaction_receipt")
            conn.execute(
                "INSERT INTO session_notification_compaction_receipts(receipt_id,created_at,row_count) "
                "VALUES(?,?,?)", (receipt, now, len(rows)),
            )
            self._failpoint("after_compaction_receipt")
            if rows:
                conn.executemany(
                    "DELETE FROM session_notifications WHERE notification_id=? AND status='acknowledged'",
                    [(row[0],) for row in rows],
                )
            self._failpoint("before_compaction_commit")
            conn.commit()
            return receipt, len(rows)
        finally:
            conn.close()
