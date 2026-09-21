"""Scoped, policy-versioned cache of memory recall packets.

One job: stop paying a synchronous remote memory round-trip on every turn when a
recent, correctly-scoped answer is already known.

Where this sits
---------------
``MemoryManager.prefetch_all`` already fans out to providers and already owns the
in-flight guard and the blocking bound (``_EXTERNAL_PREFETCH_TIMEOUT_S``). Those
are correct and are NOT duplicated here. What was missing is memory of previous
answers: every non-trivial turn re-issued the full remote lookup, so a Gateway
that answered 200 ms ago was asked again, and a Gateway that hung cost the whole
blocking bound every turn.

Freshness contract
------------------
A packet is served without touching the network while ``fresh``. Once ``fresh``
lapses but the packet is still within ``stale_ttl_s`` it is ``stale``: the caller
may inject it immediately and refresh behind the turn. Past that it is a miss.

Why a write INVALIDATES rather than deletes
-------------------------------------------
``sync_turn`` sends the finished turn to the memory backend, which can change the
answer (new fact, corrected fact, retracted fact). Deleting the packet at that
moment would make the very next turn synchronous again -- exactly the latency we
are removing. Marking it stale instead keeps a last-known-good answer that is
served once while a replacement is fetched and validated. The entry is only
replaced by a validated fetch, never cleared ahead of one.

Why an empty result is never cached
-----------------------------------
A provider returns ``""`` both for "no memories matched" and for "the backend
failed or timed out". Those are indistinguishable at this boundary, and caching
the second as if it were the first would convert a transient outage into a
persistent false negative. Only non-empty text is stored. The cost is that an
empty answer is re-fetched; the benefit is that an outage cannot silently become
"this user has no memories".

Scope safety
------------
The cache key is derived from a canonical JSON encoding of the scope tuple, so
``None`` and ``""`` cannot collide and a separator inside a session id cannot
forge a different scope. ``POLICY_VERSION`` is part of the key *and* stored on
every packet, so a packet produced under an older policy can never be served as
a current result even if it has not yet been evicted.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: Bump when the meaning of a cached packet changes. Part of every key, and
#: recorded on every packet, so old entries become unreachable rather than wrong.
POLICY_VERSION = "memory-packet-1"

#: Default grace periods. ``fresh`` avoids the network entirely; ``stale`` still
#: avoids it on the critical path but schedules a replacement.
DEFAULT_FRESH_TTL_S = 30.0
DEFAULT_STALE_TTL_S = 300.0

#: Bounded so a long-lived process cannot grow the map without limit.
DEFAULT_MAX_ENTRIES = 512

FRESH = "fresh"
STALE = "stale"
MISS = "miss"


def normalize_query(query: Optional[str]) -> str:
    """Collapse whitespace and case so trivially different spellings share a packet.

    Deliberately conservative: it does not stem, reorder, or drop stop words,
    because two queries that differ in wording can legitimately need different
    memories and merging them would serve the wrong one.
    """
    return " ".join((query or "").split()).casefold()


def make_scope(
    *,
    provider: str,
    tenant: Optional[str] = None,
    session_id: Optional[str] = None,
    workspace: Optional[str] = None,
) -> str:
    """Canonical, collision-free scope string.

    JSON is used rather than a ``|``-joined string so that a value containing the
    separator cannot forge another scope, and so ``None`` (unknown/global) stays
    distinct from ``""`` (explicitly empty).
    """
    return json.dumps(
        [provider, tenant, session_id, workspace], separators=(",", ":"), sort_keys=True
    )


def cache_key(scope: str, query: str, *, policy_version: str = POLICY_VERSION) -> str:
    """Digest of (policy, scope, normalized query)."""
    material = "\x1f".join((policy_version, scope, normalize_query(query)))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class MemoryPacket:
    """A recall result plus everything needed to reason about trusting it."""

    cache_key: str
    scope: str
    provider: str
    policy_version: str
    text: str
    fetched_at: float
    fetched_wall: float
    remote_ms: Optional[float] = None
    #: Set when a write or explicit invalidation called the answer into question.
    #: Staleness is then measured from here, so a superseded packet cannot be
    #: served indefinitely.
    invalidated_at: Optional[float] = None

    def age_s(self, now: float) -> float:
        return max(0.0, now - self.fetched_at)

    def staleness_anchor(self) -> float:
        """Clock the stale window is measured from: invalidation if superseded."""
        return self.invalidated_at if self.invalidated_at is not None else self.fetched_at

    @property
    def token_estimate(self) -> int:
        """Rough size, for context-budget telemetry. Not a tokenizer."""
        return max(0, len(self.text) // 4)


@dataclass(frozen=True)
class Recall:
    """The decision for one lookup, carrying its own provenance.

    ``served_from_cache`` and ``remote_work_performed`` are separate because a
    stale hit does both: it serves a cached packet *and* starts remote work.
    """

    state: str
    packet: Optional[MemoryPacket]
    age_s: Optional[float]
    text: str
    reason: str
    refresh_started: bool = False

    @property
    def served_from_cache(self) -> bool:
        return self.packet is not None and self.text != ""

    @property
    def stale_but_allowed(self) -> bool:
        return self.state == STALE

    def describe(self) -> Dict[str, Any]:
        return {
            "memory_cache_state": self.state,
            "memory_cache_age_s": None if self.age_s is None else round(self.age_s, 3),
            "memory_served_from_cache": self.served_from_cache,
            "memory_stale_allowed": self.stale_but_allowed,
            "memory_remote_work": self.refresh_started,
            "memory_cache_reason": self.reason,
            "memory_policy_version": self.packet.policy_version if self.packet else POLICY_VERSION,
            "memory_tokens_injected": self.packet.token_estimate if self.served_from_cache else 0,
        }


@dataclass
class _RefreshState:
    thread: Optional[threading.Thread] = None
    started_at: float = 0.0


class MemoryPacketCache:
    """Per-process packet cache with last-known-good retention and refresh coalescing.

    Thread-safe. The clock is injectable so freshness behaviour is tested
    deterministically rather than by sleeping.
    """

    def __init__(
        self,
        *,
        fresh_ttl_s: float = DEFAULT_FRESH_TTL_S,
        stale_ttl_s: float = DEFAULT_STALE_TTL_S,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        if fresh_ttl_s < 0:
            raise ValueError("fresh_ttl_s must be >= 0")
        if stale_ttl_s < fresh_ttl_s:
            raise ValueError("stale_ttl_s must be >= fresh_ttl_s")
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._fresh_ttl_s = float(fresh_ttl_s)
        self._stale_ttl_s = float(stale_ttl_s)
        self._max_entries = int(max_entries)
        self._clock = clock
        self._wall = wall
        self._lock = threading.Lock()
        self._packets: Dict[str, MemoryPacket] = {}
        self._refreshes: Dict[str, _RefreshState] = {}

    # -- introspection -----------------------------------------------------

    @property
    def fresh_ttl_s(self) -> float:
        return self._fresh_ttl_s

    @property
    def stale_ttl_s(self) -> float:
        return self._stale_ttl_s

    def __len__(self) -> int:
        with self._lock:
            return len(self._packets)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._packets),
                "inflight_refreshes": sum(
                    1 for s in self._refreshes.values() if s.thread is not None and s.thread.is_alive()
                ),
                "policy_version": POLICY_VERSION,
            }

    # -- core --------------------------------------------------------------

    def classify(self, key: str, *, now: Optional[float] = None) -> Tuple[str, Optional[MemoryPacket], Optional[float]]:
        """Freshness verdict for ``key`` without scheduling anything."""
        at = self._clock() if now is None else now
        with self._lock:
            packet = self._packets.get(key)
        if packet is None:
            return MISS, None, None
        if packet.policy_version != POLICY_VERSION:
            # Unreachable through cache_key(), but a stored packet must never be
            # trusted on the strength of its key alone.
            return MISS, None, None
        anchor = packet.staleness_anchor()
        age = max(0.0, at - anchor)
        # A superseded packet is never "fresh" no matter how recently it was
        # fetched: invalidation is a statement about correctness, not about time.
        superseded = packet.invalidated_at is not None
        if not superseded and age <= self._fresh_ttl_s:
            return FRESH, packet, packet.age_s(at)
        if age <= self._stale_ttl_s:
            return STALE, packet, packet.age_s(at)
        return MISS, None, None

    def lookup(self, key: str, *, now: Optional[float] = None) -> Recall:
        state, packet, age = self.classify(key, now=now)
        if packet is None:
            return Recall(state=MISS, packet=None, age_s=None, text="", reason="no usable packet")
        reason = "within fresh ttl" if state == FRESH else "stale within grace; refresh scheduled"
        return Recall(state=state, packet=packet, age_s=age, text=packet.text, reason=reason)

    def put(
        self,
        key: str,
        *,
        scope: str,
        provider: str,
        text: str,
        remote_ms: Optional[float] = None,
    ) -> Optional[MemoryPacket]:
        """Atomically replace a packet. Empty text is refused; see module docstring."""
        if not text or not text.strip():
            return None
        packet = MemoryPacket(
            cache_key=key,
            scope=scope,
            provider=provider,
            policy_version=POLICY_VERSION,
            text=text,
            fetched_at=self._clock(),
            fetched_wall=self._wall(),
            remote_ms=remote_ms,
        )
        with self._lock:
            # Replacement is a single assignment: a reader either sees the old
            # packet or the new one, never a gap where a good answer used to be.
            self._packets[key] = packet
            self._evict_locked()
        return packet

    def invalidate(self, scope: str) -> int:
        """Mark every packet in ``scope`` superseded, keeping them as LKG.

        Called after a write to the backend. Returns how many were marked.
        """
        at = self._clock()
        marked = 0
        with self._lock:
            for key, packet in list(self._packets.items()):
                if packet.scope != scope:
                    continue
                if packet.invalidated_at is not None:
                    continue
                self._packets[key] = MemoryPacket(**{**packet.__dict__, "invalidated_at": at})
                marked += 1
        return marked

    def drop(self, key: str) -> None:
        with self._lock:
            self._packets.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._packets.clear()

    # -- refresh coalescing ------------------------------------------------

    def start_refresh(self, key: str, work: Callable[[], Any]) -> bool:
        """Run ``work`` on a daemon thread unless an identical refresh is in flight.

        Returns True when this call started the work, False when it coalesced
        into one already running. Without this, a stale packet hit by N
        concurrent callers would issue N identical remote requests.
        """
        with self._lock:
            state = self._refreshes.get(key)
            if state is not None and state.thread is not None and state.thread.is_alive():
                return False
            holder: Dict[str, Any] = {}

            def _run() -> None:
                try:
                    work()
                except Exception as exc:  # pragma: no cover - provider errors are non-fatal
                    logger.debug("memory packet refresh failed: %s", exc)
                finally:
                    with self._lock:
                        current = self._refreshes.get(key)
                        if current is not None and current.thread is holder.get("thread"):
                            self._refreshes.pop(key, None)

            thread = threading.Thread(target=_run, name=f"memory-packet-refresh", daemon=True)
            holder["thread"] = thread
            self._refreshes[key] = _RefreshState(thread=thread, started_at=self._clock())
            thread.start()
            return True

    def _evict_locked(self) -> None:
        """Drop the oldest entries once over budget. Caller holds the lock."""
        overflow = len(self._packets) - self._max_entries
        if overflow <= 0:
            return
        ordered = sorted(self._packets.items(), key=lambda kv: kv[1].fetched_at)
        for key, _ in ordered[:overflow]:
            self._packets.pop(key, None)
