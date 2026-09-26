"""Backend-neutral session-serving contract — smallest vertical slice of RFC #23717.

Fork research, not a refactor proposal. This module defines the *serving*
contract only: atomic session lifecycle + messages + meta/titles + one
compare-and-set lease operation. Deliberately out of scope: search/FTS,
compression policy, archival/pruning, migration/import-export, gateway
routing, telegram bindings, cron — those are app-layer concerns that must
never be backend primitives (see the four competing artifacts on #23717).

The point of this slice is testability, not architecture: the accompanying
contract tests prove the *current* SQLite ``SessionDB`` satisfies this slice
unmodified, so any future backend that passes the same tests is a drop-in
replacement for the serving path. The lease op is the operation most likely
to break across substrates (the compression/turn-lease concurrency contract
is newer than every existing PostgreSQL implementation), which is why it is
part of the smallest slice rather than an add-on.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class SessionServingBackend(ABC):
    """Atomic session/message serving surface plus a CAS lease.

    Message dicts follow the ``SessionDB.append_message`` row shape
    (``role``/``content``/``tool_name``/``tool_calls``/``tool_call_id``/
    ``finish_reason``/...). Ordering guarantee: ``get_messages`` returns
    rows in insertion order (row id), never timestamp.
    """

    # ── session lifecycle ──────────────────────────────────────────────

    @abstractmethod
    def create_session(self, session_id: str, source: str) -> str:
        """Create (upsert) a session record. Returns the session_id."""

    @abstractmethod
    def ensure_session(self, session_id: str, source: str = "unknown") -> str:
        """Ensure a session row exists (upsert). Returns the session_id."""

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID, or None when it does not exist."""

    @abstractmethod
    def end_session(self, session_id: str, end_reason: str) -> None:
        """Mark a session ended. First end_reason wins."""

    @abstractmethod
    def reopen_session(self, session_id: str) -> None:
        """Clear ended_at/end_reason so a session can be resumed."""

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages. False when already absent."""

    # ── messages ───────────────────────────────────────────────────────

    @abstractmethod
    def append_message(self, session_id: str, role: str, content: Optional[str] = None,
                       **fields: Any) -> int:
        """Append one message; returns the row id. Bumps session counters."""

    @abstractmethod
    def append_messages_batch(self, session_id: str,
                              messages: List[Dict[str, Any]]) -> int:
        """Atomically append a batch; returns the number of rows inserted."""

    @abstractmethod
    def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Load messages in insertion order."""

    @abstractmethod
    def get_messages_as_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """Load messages in the conversation (role/content) view."""

    @abstractmethod
    def replace_messages(self, session_id: str,
                         messages: List[Dict[str, Any]]) -> None:
        """Atomically replace a session's messages (/retry, /undo, /compress)."""

    @abstractmethod
    def clear_messages(self, session_id: str) -> None:
        """Delete all messages for a session and reset its counters."""

    # ── meta / titles / counts ─────────────────────────────────────────

    @abstractmethod
    def get_meta(self, key: str) -> Optional[str]:
        """Read a state_meta entry."""

    @abstractmethod
    def set_meta(self, key: str, value: str) -> None:
        """Upsert a state_meta entry."""

    @abstractmethod
    def get_session_title(self, session_id: str) -> Optional[str]:
        """Get a session's title, or None."""

    @abstractmethod
    def set_session_title(self, session_id: str, title: str) -> bool:
        """Set a session's title. May raise on validation failure."""

    @abstractmethod
    def session_count(self) -> int:
        """Total number of session rows."""

    @abstractmethod
    def message_count(self, session_id: Optional[str] = None) -> int:
        """Count messages, optionally for one session."""

    # ── compare-and-set lease ──────────────────────────────────────────
    #
    # The cross-substrate hazard: ownership is decided by the holder token,
    # not by wall-clock expiry alone. A lease is acquired iff no *live*
    # holder owns it; expired locks are reclaimed transparently; only the
    # holder can refresh or release. This is the compression/turn-lease
    # semantic lifted to a named scope.

    @abstractmethod
    def lease_acquire(self, scope: str, name: str, holder: str,
                      ttl_seconds: float = 300.0) -> bool:
        """Acquire the lease iff no live holder owns it. True on success."""

    @abstractmethod
    def lease_refresh(self, scope: str, name: str, holder: str,
                      ttl_seconds: float = 300.0) -> bool:
        """Extend the lease iff ``holder`` still owns it. True on success."""

    @abstractmethod
    def lease_release(self, scope: str, name: str, holder: str) -> None:
        """Release the lease iff ``holder`` owns it; idempotent otherwise."""
