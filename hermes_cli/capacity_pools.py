"""Named host/provider capacity pools for Kanban dispatch (shadow-first).

Leases are process-local and secret-free. Default mode is shadow: receipts
are emitted, spawn is not refused, and systemd-run is not applied unless
``HERMES_KANBAN_CAPACITY_ENFORCE=1`` / ``HERMES_KANBAN_SYSTEMD_SLICE=1``.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

PRIVACY_CLASSES = ("public-oss", "company-private", "secrets")

DEFAULT_POOL_CAPS: dict[str, int] = {
    "cpu-interactive": 2,
    "cpu-batch": 8,
    "gpu-3080ti-12g": 1,
    "provider-codex": 4,
    "provider-grok": 8,
    "provider-groq": 4,
    "provider-cerebras": 1,
    "provider-gemini": 2,
    "provider-nous-free": 4,
    "provider-openrouter-free": 3,
    "github-write": 1,
    "heavy-build": 1,
}

FACTORY_KIND_ALIASES = {
    "observe": "triage",
    "triage": "triage",
    "decompose": "triage",
    "scout": "triage",
    "review": "coding",
    "implement": "coding",
    "coding": "coding",
    "primary": "coding",
    "verify": "coding",
}


def normalize_task_capacity(
    *,
    privacy_class: Optional[str] = None,
    capacity_pools: Optional[Iterable[str]] = None,
    moa_preset: Optional[str] = None,
) -> dict[str, Any]:
    pc = (privacy_class or "").strip() or None
    if pc is not None and pc not in PRIVACY_CLASSES:
        raise ValueError(f"unknown privacy_class {pc!r}; expected one of {PRIVACY_CLASSES}")
    pools: list[str] = []
    seen: set[str] = set()
    for raw in capacity_pools or ():
        name = str(raw).strip()
        if not name or name in seen:
            continue
        if name not in DEFAULT_POOL_CAPS:
            raise ValueError(f"unknown capacity pool {name!r}")
        seen.add(name)
        pools.append(name)
    preset = (moa_preset or "").strip() or None
    return {
        "privacy_class": pc,
        "capacity_pools": pools,
        "moa_preset": preset,
    }


def factory_route(kind: str) -> dict[str, Any]:
    """Map OSS factory card kinds onto MoA + pools. Public OSS only."""
    lane = FACTORY_KIND_ALIASES.get((kind or "").strip().lower(), "coding")
    if lane == "triage":
        preset = "triage-tiny"
        # Gemini free-tier 429s stall the fleet; Groq/Nous/Grok can absorb overflow.
        pools = ["cpu-batch", "provider-groq", "provider-nous-free"]
    else:
        preset = "coding-free"
        pools = ["cpu-batch", "provider-groq", "provider-nous-free", "provider-grok"]
    return {
        "privacy_class": "public-oss",
        "capacity_pools": pools,
        "moa_preset": preset,
        "model_override": preset,
        "provider_override": "moa",
    }


def systemd_slice_for(pools: Iterable[str]) -> str:
    names = set(pools or ())
    if "cpu-interactive" in names and "cpu-batch" not in names:
        return "hermes-interactive.slice"
    if "heavy-build" in names or "gpu-3080ti-12g" in names:
        return "hermes-heavy.slice"
    return "hermes-batch.slice"


def wrap_spawn_command(
    cmd: list[str],
    pools: Iterable[str],
    *,
    enforce: bool = False,
) -> list[str]:
    """Prefix systemd-run only when enforce is on. Never mutates cmd in place."""
    if not enforce:
        return list(cmd)
    slice_name = systemd_slice_for(pools)
    return [
        "systemd-run",
        "--user",
        "--collect",
        f"--slice={slice_name}",
        "--property=MemoryMax=2G",
        "--",
        *cmd,
    ]


class CapacityLeaseTable:
    """In-process atomic multi-pool leases. Not durable across gateway restarts."""

    def __init__(self, caps: Optional[Mapping[str, int]] = None) -> None:
        self._caps = dict(caps or DEFAULT_POOL_CAPS)
        self._held: dict[str, int] = {k: 0 for k in self._caps}
        self._by_task: dict[str, tuple[str, ...]] = {}
        self._lock = threading.Lock()

    def held(self, pool: str) -> int:
        with self._lock:
            return int(self._held.get(pool, 0))

    def acquire(self, task_id: str, pools: Iterable[str]) -> bool:
        wanted = tuple(dict.fromkeys(str(p) for p in pools if p))
        with self._lock:
            if task_id in self._by_task:
                return True
            for pool in wanted:
                cap = int(self._caps.get(pool, 0))
                if cap <= 0:
                    return False
                if self._held.get(pool, 0) >= cap:
                    return False
            for pool in wanted:
                self._held[pool] = self._held.get(pool, 0) + 1
            self._by_task[task_id] = wanted
            return True

    def release(self, task_id: str) -> None:
        with self._lock:
            held = self._by_task.pop(task_id, ())
            for pool in held:
                self._held[pool] = max(0, self._held.get(pool, 0) - 1)


_TABLE = CapacityLeaseTable()


def lease_table() -> CapacityLeaseTable:
    return _TABLE


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def capacity_enforce() -> bool:
    return env_flag("HERMES_KANBAN_CAPACITY_ENFORCE")


def systemd_slice_enforce() -> bool:
    return env_flag("HERMES_KANBAN_SYSTEMD_SLICE")


def _run_json(argv: list[str], timeout: float = 4.0) -> Optional[Any]:
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(data, (dict, list)):
        return data
    return None


def _first_mapping(payload: Any) -> Optional[dict[str, Any]]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                return item
    return None


def _used_pct(*candidates: Any) -> Optional[float]:
    for raw in candidates:
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return float(raw)
    return None


def provider_remaining(runner=_run_json) -> dict[str, Any]:
    """Codex/Grok remaining% from local bars. Percents only — never emails/tokens."""
    out: dict[str, Any] = {}
    raw_codex = runner(["codexbar", "usage", "--format", "json", "--provider", "codex"])
    codex = _first_mapping(raw_codex)
    if isinstance(codex, dict):
        usage = codex.get("usage") if isinstance(codex.get("usage"), dict) else codex
        secondary = usage.get("secondary") if isinstance(usage.get("secondary"), dict) else {}
        pct = _used_pct(secondary.get("usedPercent"), secondary.get("used_percent"))
        if pct is not None:
            out["codex_weekly_used_pct"] = pct
        for window in usage.get("extraRateWindows") or []:
            if not isinstance(window, dict):
                continue
            wid = str(window.get("id") or "")
            win = window.get("window") if isinstance(window.get("window"), dict) else window
            wpct = _used_pct(win.get("usedPercent"), win.get("used_percent"))
            if wpct is None:
                continue
            if wid == "codex-spark":
                out["codex_5h_used_pct"] = wpct
            elif wid == "codex-spark-weekly":
                out["codex_spark_weekly_used_pct"] = wpct
    raw_quota = runner(["quota-axi", "--json"])
    quota = raw_quota if isinstance(raw_quota, dict) else None
    if quota:
        for prov in quota.get("providers") or []:
            if not isinstance(prov, dict):
                continue
            name = str(prov.get("provider") or "")
            windows = prov.get("windows") or []
            if name == "codex" and "codex_weekly_used_pct" not in out:
                for win in windows:
                    if isinstance(win, dict) and win.get("id") == "weekly":
                        pct = _used_pct(win.get("percentUsed"))
                        if pct is not None:
                            out["codex_weekly_used_pct"] = pct
            if name == "grok":
                for win in windows:
                    if not isinstance(win, dict):
                        continue
                    if win.get("id") in {"credits", "weekly"}:
                        pct = _used_pct(win.get("percentUsed"))
                        if pct is not None:
                            out["grok_weekly_used_pct"] = pct
                        rem = _used_pct(win.get("percentRemaining"))
                        if rem is not None:
                            out["grok_weekly_remaining_pct"] = rem
                        break
    return out


def build_receipt(
    *,
    task_id: str,
    privacy_class: Optional[str],
    pools: Iterable[str],
    moa_preset: Optional[str],
    load1: Optional[float],
    nproc: Optional[int],
    provider_remaining: Mapping[str, Any],
    would_block: bool,
    shadow: bool,
    chosen_model: Optional[str] = None,
    chosen_provider: Optional[str] = None,
    board: Optional[str] = None,
) -> dict[str, Any]:
    pool_list = [str(p) for p in pools if p]
    return {
        "schema": "asg-capacity-receipt/v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "board": board,
        "privacy_class": privacy_class,
        "pools": pool_list,
        "moa_preset": moa_preset,
        "chosen_model": chosen_model,
        "chosen_provider": chosen_provider,
        "load1": load1,
        "nproc": nproc,
        "provider_remaining": dict(provider_remaining),
        "would_block": bool(would_block),
        "shadow": bool(shadow),
        "fallback": "none",
        "intended_slice": systemd_slice_for(pool_list),
    }


def persist_receipt(receipt: Mapping[str, Any], path: Optional[Path] = None) -> Path:
    dest = path or (
        Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
        / "kanban"
        / "capacity-receipts.jsonl"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(receipt), ensure_ascii=False) + "\n")
    return dest


def pools_for_task(task: Any) -> list[str]:
    raw = getattr(task, "capacity_pools", None)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            raw = parsed
        except json.JSONDecodeError:
            raw = [p.strip() for p in raw.split(",") if p.strip()]
    if isinstance(raw, (list, tuple)):
        return [str(p) for p in raw if p]
    return ["cpu-batch"]


def shadow_admit(task: Any, *, load1: Optional[float] = None, nproc: Optional[int] = None) -> dict[str, Any]:
    """Always allow spawn in shadow. Optionally hold a lease when enforcing."""
    pools = pools_for_task(task)
    task_id = getattr(task, "id", "unknown")
    enforce = capacity_enforce()
    blocked = False
    if enforce:
        blocked = not _TABLE.acquire(task_id, pools)
    remaining = provider_remaining()
    return build_receipt(
        task_id=task_id,
        privacy_class=getattr(task, "privacy_class", None),
        pools=pools,
        moa_preset=getattr(task, "moa_preset", None),
        load1=load1,
        nproc=nproc,
        provider_remaining=remaining,
        would_block=blocked,
        shadow=not enforce,
        chosen_model=getattr(task, "model_override", None),
        chosen_provider=getattr(task, "provider_override", None),
    )
