from __future__ import annotations

import math
from typing import Optional

from hermes_asg.types import (
    AdmissionClass,
    BreakerState,
    CapacityKey,
    KeyState,
    PrivacyClass,
    Rejected,
    RoutingReceipt,
)


class ShadowAsgController:
    """Library-only shadow ASG. Never mutates live Hermes routing."""

    def __init__(
        self,
        *,
        global_limit: int = 10,
        reserved_frac: float = 0.2,
        additive: int = 1,
        multiplicative: float = 0.5,
        breaker_threshold: int = 3,
        breaker_reset_s: float = 60.0,
        probe_interval_s: float = 30.0,
        explorer_eps: float = 0.1,
        explorer_seed: int = 0,
        now: float = 0.0,
    ) -> None:
        self.global_limit = global_limit
        self.reserved_frac = reserved_frac
        self.additive = additive
        self.multiplicative = multiplicative
        self.breaker_threshold = breaker_threshold
        self.breaker_reset_s = breaker_reset_s
        self.probe_interval_s = probe_interval_s
        self.explorer_eps = explorer_eps
        self.explorer_seed = explorer_seed
        self._now = now
        self._keys: dict[CapacityKey, KeyState] = {}
        self._global_inflight = 0
        self._class_inflight: dict[AdmissionClass, int] = {
            AdmissionClass.INTERACTIVE: 0,
            AdmissionClass.BATCH: 0,
            AdmissionClass.PROBE: 0,
        }
        self._rng = _Lcg(explorer_seed)

    @property
    def reserved_interactive(self) -> int:
        return max(1, math.ceil(self.global_limit * self.reserved_frac))

    def now(self) -> float:
        return self._now

    def tick(self, ts: float) -> None:
        self._now = ts
        self._expire_workers()
        self._maybe_half_open()

    def register_key(
        self,
        key: CapacityKey,
        *,
        declared_limit: Optional[int] = None,
        privacy_class: PrivacyClass = PrivacyClass.THIRD_PARTY,
        cost_per_1k: float = 0.0,
        worker_max_slots: int = 0,
        worker_ttl_s: float = 30.0,
    ) -> None:
        st = self._keys.setdefault(key, KeyState())
        st.declared_limit = declared_limit
        st.privacy_class = privacy_class
        st.cost_per_1k = cost_per_1k
        st.worker_max_slots = worker_max_slots
        st.worker_ttl_s = worker_ttl_s
        # Start at min(declared, conservative_floor=1). Unknown declared → 1.
        st.aimd_limit = 1 if not declared_limit else min(declared_limit, 1)
        st.worker_last_heartbeat = self._now
        st.worker_alive = True

    def heartbeat_worker(self, key: CapacityKey, *, max_slots: int, ttl_s: float = 30.0) -> None:
        st = self._require(key)
        st.worker_last_heartbeat = self._now
        st.worker_max_slots = max_slots
        st.worker_ttl_s = ttl_s
        st.worker_alive = True

    def observe(
        self,
        key: CapacityKey,
        *,
        classified: str,
        remaining: Optional[int] = None,
        retry_after_s: Optional[float] = None,
        latency_ms: Optional[float] = None,
        success: Optional[bool] = None,
    ) -> None:
        st = self._require(key)
        if latency_ms is not None:
            st.latency_ewma_ms = (
                latency_ms if st.latency_ewma_ms == 0 else 0.2 * latency_ms + 0.8 * st.latency_ewma_ms
            )
        if classified == "rate_limit":
            if remaining == 0 or remaining is None:
                self._aimd_decrease(st)
            if (retry_after_s or 0) >= 60:
                st.consecutive_capacity_failures += 1
                if st.consecutive_capacity_failures >= self.breaker_threshold:
                    self._open_breaker(st)
        elif classified == "overloaded":
            self._aimd_decrease(st)
            st.consecutive_capacity_failures += 1
            if st.consecutive_capacity_failures >= self.breaker_threshold:
                self._open_breaker(st)
        elif classified == "billing":
            st.billing_frozen = True
        elif classified in ("auth", "unauthorized"):
            # auth ≠ capacity — do not trip capacity breaker
            pass
        elif classified == "ok" or success is True:
            st.consecutive_capacity_failures = 0
            if st.breaker_state == BreakerState.HALF_OPEN:
                st.breaker_state = BreakerState.CLOSED
            self._aimd_increase(st)
            if success is not False:
                st.success_ewma = 0.2 * 1.0 + 0.8 * st.success_ewma

    def observe_probe(self, key: CapacityKey, *, classified: str) -> None:
        st = self._require(key)
        st.last_probe_ts = self._now
        if classified in ("rate_limit", "overloaded"):
            self._aimd_decrease(st)
        elif classified in ("auth", "unauthorized", "billing"):
            if classified == "billing":
                st.billing_frozen = True
            # auth does not trip capacity breaker
        elif classified == "ok":
            self._aimd_increase(st)
            if st.breaker_state == BreakerState.HALF_OPEN:
                st.breaker_state = BreakerState.CLOSED

    def can_probe(self, key: CapacityKey) -> bool:
        st = self._require(key)
        return (self._now - st.last_probe_ts) >= self.probe_interval_s

    def admit(
        self,
        request_id: str,
        *,
        admission_class: AdmissionClass | str,
        required_privacy: PrivacyClass = PrivacyClass.THIRD_PARTY,
        max_cost_per_1k: Optional[float] = None,
        preferred_keys: Optional[list[CapacityKey]] = None,
    ) -> RoutingReceipt:
        if isinstance(admission_class, str):
            try:
                admission_class = AdmissionClass(admission_class)
            except ValueError:
                admission_class = AdmissionClass.BATCH  # fail closed

        self._expire_workers()
        self._maybe_half_open()

        reserved = self.reserved_interactive
        free = self.global_limit - self._global_inflight
        reserved_held = False
        if admission_class == AdmissionClass.BATCH:
            if free <= reserved:
                return self._receipt(
                    request_id,
                    None,
                    (),
                    (Rejected(CapacityKey("*", "*", "*", "*"), "reserved_interactive"),),
                    admission_class,
                    False,
                    False,
                    False,
                    "batch_blocked_by_reserved",
                )
        elif admission_class == AdmissionClass.PROBE:
            if free <= 0:
                return self._receipt(
                    request_id, None, (), (), admission_class, False, False, False, "no_global_slot"
                )
        else:  # interactive
            if free <= 0:
                return self._receipt(
                    request_id, None, (), (), admission_class, False, False, False, "no_global_slot"
                )
            leftover = max(0, free - reserved)
            reserved_held = leftover == 0

        keys = preferred_keys or list(self._keys.keys())
        rejected: list[Rejected] = []
        eligible: list[CapacityKey] = []
        for k in keys:
            st = self._keys.get(k)
            if st is None:
                rejected.append(Rejected(k, "unknown_key"))
                continue
            if not st.worker_alive:
                rejected.append(Rejected(k, "worker_ttl_expired"))
                continue
            if st.billing_frozen:
                rejected.append(Rejected(k, "billing_freeze"))
                continue
            if st.privacy_class.rank() < required_privacy.rank():
                rejected.append(Rejected(k, "privacy_hard_filter"))
                continue
            if max_cost_per_1k is not None and st.cost_per_1k > max_cost_per_1k:
                rejected.append(Rejected(k, "cost_hard_filter"))
                continue
            if st.breaker_state == BreakerState.OPEN:
                rejected.append(Rejected(k, "breaker_open"))
                continue
            if st.breaker_state == BreakerState.HALF_OPEN and st.observed_inflight >= 1:
                rejected.append(Rejected(k, "half_open_one_trial"))
                continue
            if st.observed_inflight >= st.aimd_limit:
                rejected.append(Rejected(k, "aimd_full"))
                continue
            eligible.append(k)

        if not eligible:
            return self._receipt(
                request_id,
                None,
                (),
                tuple(rejected),
                admission_class,
                reserved_held,
                False,
                False,
                "no_eligible_key",
            )

        explorer_used = False
        leftover_slots = max(0, (self.global_limit - self._global_inflight) - reserved)
        if leftover_slots > 0 and self._rng.next() < self.explorer_eps and len(eligible) > 1:
            chosen = eligible[self._rng.next_int(len(eligible))]
            explorer_used = True
        else:
            chosen = self._best(eligible)

        st = self._keys[chosen]
        st.observed_inflight += 1
        self._global_inflight += 1
        self._class_inflight[admission_class] += 1
        return RoutingReceipt(
            request_id=request_id,
            chosen_key=chosen,
            candidates=tuple(eligible),
            rejected=tuple(rejected),
            aimd_limit=st.aimd_limit,
            inflight=st.observed_inflight,
            admission_class=admission_class,
            reserved_held=reserved_held,
            explorer_used=explorer_used,
            admitted=True,
            ts=self._now,
            reason="admitted_shadow",
            shadow=True,
            live_path_unchanged=True,
        )

    def release(self, key: CapacityKey, admission_class: AdmissionClass | str) -> None:
        if isinstance(admission_class, str):
            try:
                admission_class = AdmissionClass(admission_class)
            except ValueError:
                admission_class = AdmissionClass.BATCH
        st = self._keys.get(key)
        if st and st.observed_inflight > 0:
            st.observed_inflight -= 1
        if self._global_inflight > 0:
            self._global_inflight -= 1
        if self._class_inflight[admission_class] > 0:
            self._class_inflight[admission_class] -= 1

    def snapshot(self, key: CapacityKey) -> KeyState:
        return self._require(key)

    def replay_choice(
        self,
        *,
        eligible: list[CapacityKey],
        explorer_seed: int,
        explorer_eps: float,
        leftover_slots: int,
    ) -> tuple[CapacityKey, bool]:
        rng = _Lcg(explorer_seed)
        explorer_used = False
        if leftover_slots > 0 and rng.next() < explorer_eps and len(eligible) > 1:
            return eligible[rng.next_int(len(eligible))], True
        return self._best(eligible), False

    def _best(self, eligible: list[CapacityKey]) -> CapacityKey:
        def score(k: CapacityKey) -> tuple:
            st = self._keys[k]
            headroom = st.aimd_limit - st.observed_inflight
            return (-headroom, st.latency_ewma_ms, k.provider, k.model, k.account_id, k.worker_id)

        return sorted(eligible, key=score)[0]

    def _aimd_increase(self, st: KeyState) -> None:
        nxt = st.aimd_limit + self.additive
        if st.declared_limit is not None:
            nxt = min(st.declared_limit, nxt)
        st.aimd_limit = max(1, nxt)

    def _aimd_decrease(self, st: KeyState) -> None:
        st.aimd_limit = max(1, math.floor(st.aimd_limit * self.multiplicative))

    def _open_breaker(self, st: KeyState) -> None:
        st.breaker_state = BreakerState.OPEN
        st.breaker_opened_at = self._now

    def _maybe_half_open(self) -> None:
        for st in self._keys.values():
            if st.breaker_state == BreakerState.OPEN and (self._now - st.breaker_opened_at) >= self.breaker_reset_s:
                st.breaker_state = BreakerState.HALF_OPEN

    def _expire_workers(self) -> None:
        for st in self._keys.values():
            if st.worker_ttl_s and (self._now - st.worker_last_heartbeat) > st.worker_ttl_s:
                st.worker_alive = False
                st.worker_max_slots = 0

    def _require(self, key: CapacityKey) -> KeyState:
        if key not in self._keys:
            raise KeyError(key)
        return self._keys[key]

    def _receipt(
        self,
        request_id: str,
        chosen: Optional[CapacityKey],
        candidates: tuple[CapacityKey, ...],
        rejected: tuple[Rejected, ...],
        admission_class: AdmissionClass,
        reserved_held: bool,
        explorer_used: bool,
        admitted: bool,
        reason: str,
    ) -> RoutingReceipt:
        aimd = inflight = None
        if chosen is not None:
            st = self._keys[chosen]
            aimd, inflight = st.aimd_limit, st.observed_inflight
        return RoutingReceipt(
            request_id=request_id,
            chosen_key=chosen,
            candidates=candidates,
            rejected=rejected,
            aimd_limit=aimd,
            inflight=inflight,
            admission_class=admission_class,
            reserved_held=reserved_held,
            explorer_used=explorer_used,
            admitted=admitted,
            ts=self._now,
            reason=reason,
            shadow=True,
            live_path_unchanged=True,
        )


class _Lcg:
    def __init__(self, seed: int) -> None:
        self.s = seed & 0xFFFFFFFF

    def next(self) -> float:
        self.s = (1664525 * self.s + 1013904223) & 0xFFFFFFFF
        return self.s / 0x100000000

    def next_int(self, n: int) -> int:
        return int(self.next() * n) % n
