"""Decision windows: a proactive job fires when the person can use it, not only when it is due.

A job may declare a ``window_class``:

- ``peak``: it asks for a decision; speak while focus is high.
- ``trough``: a review or an easy read; fine when energy dips.
- ``wind_down``: an end-of-day question; only once the evening has started.
- ``anytime``: a capture or a short note; any open moment.

A ``WindowProvider`` reports the window open now (``current(now)``); a plugin registers one with
``ctx.register_window_provider``. With none registered, ``ALWAYS_ANYTIME`` reports ``anytime``,
which opens every class, so a configured job behaves as it did before the field existed.

``stale_after_s`` bounds how late an occurrence may still fire, counted from its due instant: a
reminder held (or caught up after downtime) past it is noise, so it is dropped instead.

``gate`` is pure: it reads the job, the instant and the provider and returns (fire, reason). The
tick (``cron.scheduler_window_gate``) applies the verdict. Design:
https://github.com/NousResearch/hermes-agent/issues/158538
"""

from __future__ import annotations

import math
from datetime import datetime
from enum import Enum
from typing import Any, NamedTuple, Optional, Protocol, runtime_checkable


class WindowClass(str, Enum):
    PEAK = "peak"
    TROUGH = "trough"
    ANYTIME = "anytime"
    WIND_DOWN = "wind_down"


@runtime_checkable
class WindowProvider(Protocol):
    def current(self, now: datetime) -> Optional[WindowClass | str]:
        """The window open at *now*, or None when the provider cannot tell."""


class _AlwaysAnytime:
    """The provider used when no plugin registers one: every window is open."""

    def current(self, now: datetime) -> WindowClass:
        return WindowClass.ANYTIME


ALWAYS_ANYTIME: WindowProvider = _AlwaysAnytime()


class GateVerdict(NamedTuple):
    fire: bool
    reason: str  # one line; a held job shows it as its ``last_fire_error``


def normalize_window_class(value: Any) -> Optional[str]:
    """A job's ``window_class`` as stored (``None`` = no window: today's behaviour)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, WindowClass):
        return value.value
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in WindowClass._value2member_map_:
            return clean
    raise ValueError(
        f"window_class must be one of {', '.join(c.value for c in WindowClass)}, not {value!r}.")


def normalize_stale_after_s(value: Any) -> Optional[float]:
    """A job's ``stale_after_s`` as stored: positive seconds, or ``None`` (never stale)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError("stale_after_s must be a number of seconds, not a boolean.")
    try:
        seconds = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"stale_after_s must be a number of seconds, not {value!r}.") from exc
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError(f"stale_after_s must be a positive number of seconds, not {value!r}.")
    return seconds


def _manual_run(job: dict) -> bool:
    """``hermes cron run`` stamps the same instant into both fields; an operator's run-now is never held."""
    return bool(job.get("manual_run_at")) and job.get("manual_run_at") == job.get("next_run_at")


def _due_age_seconds(job: dict, now: datetime) -> Optional[float]:
    raw = job.get("next_run_at")
    if not raw:
        return None
    due = datetime.fromisoformat(raw)
    if due.tzinfo is None:
        due = due.replace(tzinfo=now.tzinfo)
    return (now - due).total_seconds()


def is_stale(job: dict, now: datetime) -> bool:
    """True when the due occurrence is older than the job's ``stale_after_s``."""
    limit = job.get("stale_after_s")
    if limit is None or _manual_run(job):
        return False
    age = _due_age_seconds(job, now)
    return age is not None and age > limit


def _as_window(value: Any) -> Optional[WindowClass]:
    if isinstance(value, WindowClass):
        return value
    return WindowClass._value2member_map_.get(value) if isinstance(value, str) else None


def gate(job: dict, now: datetime, provider: WindowProvider) -> GateVerdict:
    """Whether a due *job* fires at *now*, with a one-line reason.

    Order: a manual run fires; a stale occurrence does not; no ``window_class`` or ``anytime``
    fires; an unknown window holds; ``anytime`` from the provider opens every class; a matching
    window fires; any other window holds.
    """
    if _manual_run(job):
        return GateVerdict(True, "manual run")
    if is_stale(job, now):
        age = _due_age_seconds(job, now)
        return GateVerdict(False, f"stale: due {age:.0f}s ago, past stale_after_s={job['stale_after_s']:g}")
    wanted = _as_window(job.get("window_class"))
    if wanted is None or wanted is WindowClass.ANYTIME:
        return GateVerdict(True, "no window needed")
    open_now = _as_window(provider.current(now))
    if open_now is None:
        return GateVerdict(False, f"window unknown: holds the {wanted.value} job until the provider knows")
    if open_now is WindowClass.ANYTIME or open_now is wanted:
        return GateVerdict(True, f"{open_now.value} window open")
    return GateVerdict(False, f"{open_now.value} window open: holds the {wanted.value} job")
