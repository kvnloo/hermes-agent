"""SQLite implementation of the session-serving contract — composition, not refactor.

``SqliteSessionServingBackend`` wraps an existing ``SessionDB`` and delegates
every contract method to it. Nothing in the storage layer changes; the point
is machine-checkable: the current implementation already satisfies the
serving slice, so any future backend passing the same contract tests is a
drop-in replacement for the serving path.

Lease scope: only ``"compression"`` is supported today (mapped onto the
compression-lock primitives, whose holder-not-clock ownership semantics are
exactly the contract's). Other scopes raise ``ValueError`` — an honest
limitation of this slice, not of the contract.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from hermes_state import SessionDB
from hermes_state_serving_backend import SessionServingBackend


class SqliteSessionServingBackend(SessionServingBackend):
    """Serve the contract from a live ``SessionDB`` instance."""

    _LEASE_SCOPE = "compression"

    def __init__(self, session_db: SessionDB) -> None:
        self._db = session_db

    # ── session lifecycle ──────────────────────────────────────────

    def create_session(self, session_id: str, source: str) -> str:
        return self._db.create_session(session_id, source)

    def ensure_session(self, session_id: str, source: str = "unknown") -> str:
        return self._db.ensure_session(session_id, source)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._db.get_session(session_id)

    def end_session(self, session_id: str, end_reason: str) -> None:
        self._db.end_session(session_id, end_reason)

    def reopen_session(self, session_id: str) -> None:
        self._db.reopen_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self._db.delete_session(session_id)

    # ── messages ───────────────────────────────────────────────────

    def append_message(self, session_id: str, role: str,
                       content: Optional[str] = None, **fields: Any) -> int:
        return self._db.append_message(session_id, role, content=content, **fields)

    def append_messages_batch(self, session_id: str,
                              messages: List[Dict[str, Any]]) -> int:
        return self._db.append_messages_batch(session_id, messages)

    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        return self._db.get_messages(session_id)

    def get_messages_as_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        return self._db.get_messages_as_conversation(session_id)

    def replace_messages(self, session_id: str,
                         messages: List[Dict[str, Any]]) -> None:
        self._db.replace_messages(session_id, messages)

    def clear_messages(self, session_id: str) -> None:
        self._db.clear_messages(session_id)

    # ── meta / titles / counts ─────────────────────────────────────

    def get_meta(self, key: str) -> Optional[str]:
        return self._db.get_meta(key)

    def set_meta(self, key: str, value: str) -> None:
        self._db.set_meta(key, value)

    def get_session_title(self, session_id: str) -> Optional[str]:
        return self._db.get_session_title(session_id)

    def set_session_title(self, session_id: str, title: str) -> bool:
        return self._db.set_session_title(session_id, title)

    def session_count(self) -> int:
        return self._db.session_count()

    def message_count(self, session_id: Optional[str] = None) -> int:
        return self._db.message_count(session_id)

    # ── compare-and-set lease ──────────────────────────────────────

    def _check_scope(self, scope: str) -> None:
        if scope != self._LEASE_SCOPE:
            raise ValueError(
                f"unsupported lease scope {scope!r}: this adapter only serves "
                f"{self._LEASE_SCOPE!r}"
            )

    def lease_acquire(self, scope: str, name: str, holder: str,
                      ttl_seconds: float = 300.0) -> bool:
        self._check_scope(scope)
        return self._db.try_acquire_compression_lock(
            name, holder, ttl_seconds=ttl_seconds)

    def lease_refresh(self, scope: str, name: str, holder: str,
                      ttl_seconds: float = 300.0) -> bool:
        self._check_scope(scope)
        return self._db.refresh_compression_lock(
            name, holder, ttl_seconds=ttl_seconds)

    def lease_release(self, scope: str, name: str, holder: str) -> None:
        self._check_scope(scope)
        self._db.release_compression_lock(name, holder)
