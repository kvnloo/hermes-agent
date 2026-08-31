from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AdmissionClass(str, Enum):
    INTERACTIVE = "interactive"
    BATCH = "batch"
    PROBE = "probe"


class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class PrivacyClass(str, Enum):
    LOCAL = "local"
    PRIVATE_CLOUD = "private_cloud"
    THIRD_PARTY = "third_party"

    def rank(self) -> int:
        return {self.LOCAL: 3, self.PRIVATE_CLOUD: 2, self.THIRD_PARTY: 1}[self]


@dataclass(frozen=True)
class CapacityKey:
    provider: str
    model: str
    account_id: str
    worker_id: str


@dataclass
class KeyState:
    declared_limit: Optional[int] = None
    observed_inflight: int = 0
    aimd_limit: int = 1
    latency_ewma_ms: float = 0.0
    success_ewma: float = 1.0
    cost_per_1k: float = 0.0
    privacy_class: PrivacyClass = PrivacyClass.THIRD_PARTY
    last_probe_ts: float = 0.0
    breaker_state: BreakerState = BreakerState.CLOSED
    consecutive_capacity_failures: int = 0
    breaker_opened_at: float = 0.0
    billing_frozen: bool = False
    worker_last_heartbeat: float = 0.0
    worker_ttl_s: float = 30.0
    worker_max_slots: int = 0
    worker_alive: bool = True


@dataclass(frozen=True)
class Rejected:
    key: CapacityKey
    reason: str


@dataclass(frozen=True)
class RoutingReceipt:
    request_id: str
    chosen_key: Optional[CapacityKey]
    candidates: tuple[CapacityKey, ...]
    rejected: tuple[Rejected, ...]
    aimd_limit: Optional[int]
    inflight: Optional[int]
    admission_class: AdmissionClass
    reserved_held: bool
    explorer_used: bool
    admitted: bool
    ts: float
    reason: str = ""
    shadow: bool = True
    live_path_unchanged: bool = True
