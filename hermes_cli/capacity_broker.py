"""Broker between host resources and Kanban/MoA orchestration.

Recommend-only by default. Never overwrites a pinned task model.
Never sends secrets/company-private work to OpenCode or :free lanes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from hermes_cli.capacity_pools import factory_route

COMPUTE_ELEVATED = 0.85
COMPUTE_CRITICAL = 1.25
GROK_EXHAUST_PCT = 90.0
CODEX_EXHAUST_PCT = 90.0


@dataclass
class BrokerDecision:
    work_kind: str
    privacy_class: str
    moa_preset: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    pools: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    pinned: bool = False
    defer: bool = False
    applied: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "work_kind": self.work_kind,
            "privacy_class": self.privacy_class,
            "moa_preset": self.moa_preset,
            "model": self.model,
            "provider": self.provider,
            "pools": list(self.pools),
            "reasons": list(self.reasons),
            "pinned": self.pinned,
            "defer": self.defer,
            "applied": self.applied,
        }


def _load_ratio(load1: Optional[float], nproc: Optional[int]) -> Optional[float]:
    if not isinstance(load1, (int, float)) or not isinstance(nproc, int):
        return None
    if nproc <= 0:
        return None
    return float(load1) / float(nproc)


def _used(remaining: Mapping[str, Any], key: str) -> Optional[float]:
    raw = remaining.get(key)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw)
    return None


def recommend(
    *,
    privacy_class: str,
    work_kind: str,
    load1: Optional[float] = None,
    nproc: Optional[int] = None,
    remaining: Optional[Mapping[str, Any]] = None,
    pinned_model: Optional[str] = None,
    pinned_provider: Optional[str] = None,
    apply: bool = False,
) -> BrokerDecision:
    pc = (privacy_class or "company-private").strip() or "company-private"
    kind = (work_kind or "coding").strip().lower()
    remaining = remaining or {}
    reasons: list[str] = []
    decision = BrokerDecision(work_kind=kind, privacy_class=pc, reasons=reasons)

    ratio = _load_ratio(load1, nproc)
    if ratio is not None and ratio >= COMPUTE_CRITICAL:
        decision.defer = True
        reasons.append("compute_critical")
    elif ratio is not None and ratio >= COMPUTE_ELEVATED:
        reasons.append("compute_elevated")

    pin_model = (pinned_model or "").strip() or None
    pin_provider = (pinned_provider or "").strip() or None
    if pin_model:
        decision.pinned = True
        decision.model = pin_model
        decision.provider = pin_provider
        if pin_provider == "moa":
            decision.moa_preset = pin_model
        decision.pools = ["cpu-batch"] if kind != "interactive" else ["cpu-interactive"]
        reasons.append("respect_existing_pin")
        _annotate_private_pools(decision)
        return decision

    if kind == "interactive":
        grok_used = _used(remaining, "grok_weekly_used_pct")
        if grok_used is not None and grok_used >= GROK_EXHAUST_PCT:
            decision.provider = "openai-codex"
            decision.model = "gpt-5.6-sol"
            decision.pools = ["cpu-interactive", "provider-codex"]
            reasons.append("grok_weekly_exhausted")
        else:
            decision.provider = "xai-oauth"
            decision.model = "grok-4.6"
            decision.pools = ["cpu-interactive", "provider-grok"]
            reasons.append("interactive_grok")
        decision.applied = bool(apply)
        return decision

    if pc in {"secrets", "company-private"}:
        decision.provider = "openai-codex"
        decision.model = "gpt-5.6-sol" if kind in {"coding", "review", "implement"} else "gpt-5.6-terra"
        decision.pools = ["cpu-batch", "provider-codex"]
        reasons.append("private_no_free_lanes")
        decision.applied = bool(apply)
        return decision

    # public-oss
    route = factory_route(kind)
    decision.moa_preset = route["moa_preset"]
    decision.model = route["model_override"]
    decision.provider = route["provider_override"]
    decision.pools = list(route["capacity_pools"])
    reasons.append("public_oss_factory_route")
    decision.applied = bool(apply)
    return decision


def _annotate_private_pools(decision: BrokerDecision) -> None:
    if decision.privacy_class in {"secrets", "company-private"}:
        decision.pools = [p for p in decision.pools if not p.startswith("provider-groq")]
        if "cpu-interactive" not in decision.pools and decision.work_kind == "interactive":
            decision.pools.insert(0, "cpu-interactive")


def recommend_for_task(task: Any, *, load1=None, nproc=None, remaining=None, apply: bool = False) -> BrokerDecision:
    kind = getattr(task, "moa_preset", None) and "coding" or "coding"
    title = (getattr(task, "title", None) or "").lower()
    if "triage" in title or "observe" in title or "scout" in title:
        kind = "observe"
    if "review" in title or "verify" in title:
        kind = "review"
    return recommend(
        privacy_class=getattr(task, "privacy_class", None) or "company-private",
        work_kind=kind,
        load1=load1,
        nproc=nproc,
        remaining=remaining,
        pinned_model=getattr(task, "model_override", None),
        pinned_provider=getattr(task, "provider_override", None),
        apply=apply,
    )
