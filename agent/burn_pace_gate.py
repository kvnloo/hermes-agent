"""Pace-aware admission for subscription pool rows.

burn-pace (~/.local/bin/burn-pace) appends one JSON reading per probe to
~/.z0int/state/posture/burn-pace.jsonl. ~/.config/burn-gate/pool-lanes.json maps
pool row labels to burn-pace lanes per provider, e.g. {"anthropic": {"claude-ultra": "claude3"}}.

For a mapped row: deny it when the weekly window is >= USED_STOP or the pace ratio is
>= RATIO_STOP, and order the rows that remain by pace ratio, coolest first. A row with
no mapping, or a provider with no mapping, passes through unchanged. If the reading is
stale or missing, every mapped row is denied (fail closed). Owner override:
HERMES_BURN_GATE_OVERRIDE=1.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

STALE_S = 30 * 60
USED_STOP = 95.0
RATIO_STOP = 1.5
_CACHE_S = 60.0
_cache: dict = {"at": 0.0, "key": None, "val": None}


def _paths():
    home = Path(os.environ.get("BURN_GATE_HOME") or Path.home())
    return home / ".z0int/state/posture/burn-pace.jsonl", home / ".config/burn-gate/pool-lanes.json"


def _last_reading(samples):
    try:
        with samples.open("rb") as f:
            f.seek(0, 2)
            f.seek(max(f.tell() - 65536, 0))
            lines = f.read().decode(errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return None


def _load():
    samples, lanes_path = _paths()
    try:
        key = (str(samples), samples.stat().st_mtime, lanes_path.stat().st_mtime)
    except OSError:
        key = None
    now = time.monotonic()
    if _cache["key"] == key and now - _cache["at"] < _CACHE_S:
        return _cache["val"]
    try:
        lanes = json.loads(lanes_path.read_text())
    except (OSError, ValueError):
        lanes = {}
    val = (lanes, _last_reading(samples))
    _cache.update(at=now, key=key, val=val)
    return val


def verdict(lane: str, reading) -> tuple[bool, float, str]:
    """(allowed, pace_ratio_for_sorting, reason)."""
    try:
        age = time.time() - datetime.fromisoformat(reading["at"]).timestamp()
    except (TypeError, KeyError, ValueError):
        return False, 0.0, "no burn-pace reading"
    if age > STALE_S:
        return False, 0.0, f"burn-pace reading {int(age // 60)} min old"
    row = (reading.get("lanes") or {}).get(lane) or {}
    used, ratio = row.get("weekly_used_pct"), row.get("pace_ratio")
    if used is None:
        return False, 0.0, f"lane {lane} missing from burn-pace"
    if used >= USED_STOP:
        return False, 0.0, f"lane {lane} weekly {used}% used, resets in {row.get('hours_to_reset')}h"
    if ratio is not None and ratio >= RATIO_STOP:
        return False, 0.0, f"lane {lane} pace {ratio}x sustainable"
    return True, ratio if ratio is not None else 0.0, f"lane {lane} {used}% used, pace {ratio}"


def admit(provider: str, entries: list) -> list:
    """Filter and order *entries* (PooledCredential-like, with .label) for *provider*."""
    if not entries or os.environ.get("HERMES_BURN_GATE_OVERRIDE") == "1":
        return entries
    lanes, reading = _load()
    mapping = lanes.get(provider) if isinstance(lanes, dict) else None
    if not mapping:
        return entries
    kept, denied = [], []
    for idx, entry in enumerate(entries):
        lane = mapping.get(getattr(entry, "label", None) or "")
        if not lane:
            kept.append((1.0, idx, entry))
            continue
        ok, ratio, why = verdict(lane, reading)
        if ok:
            kept.append((ratio, idx, entry))
        else:
            denied.append(f"{entry.label}: {why}")
    if denied:
        logger.warning("burn-pace gate (%s) skipped %s", provider, "; ".join(denied))
    if not kept:
        logger.error("burn-pace gate (%s): every subscription row is over pace; refusing to drain one "
                     "(override: HERMES_BURN_GATE_OVERRIDE=1)", provider)
    return [e for _r, _i, e in sorted(kept, key=lambda t: (t[0], t[1]))]
