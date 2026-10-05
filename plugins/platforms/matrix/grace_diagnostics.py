"""Observability for Matrix startup filtering; never changes event admission."""
import logging
import time

logger = logging.getLogger("plugins.platforms.matrix.adapter")


def reset_grace_diagnostics(adapter) -> None:
    """Reset the once-only drop notice and consecutive-drop clock-skew warning state."""
    # Clock-skew detection: count grace-check drops that happen well after startup (i.e. not
    # initial-sync backfill). If the host's system clock is set ahead of real time, the startup grace
    # check `event_ts < startup_ts - 5` silently drops every live message. See #12614 — the symptom is
    # "bot joins rooms but never replies". Drops only count when their skew matches the first sampled
    # drop (within 60s), so varied-age backfill from freshly-invited rooms doesn't trip the heuristic.
    adapter._late_grace_drops: int = 0
    adapter._late_grace_skew: float = 0.0
    adapter._clock_skew_warned: bool = False
    adapter._startup_grace_noted: bool = False


def note_grace_drop(adapter, event_ts: float) -> None:
    """Clock-skew heuristic for grace-check drops well after startup. A host clock set ahead of
    real time makes every live event look "older than startup" and the bot silently never
    replies. Warn once when drops keep happening >30s after startup with a *consistent* skew —
    unlike backfill from a freshly invited room, whose event ages vary widely and reset the counter."""
    if not adapter._startup_grace_noted:
        logger.info(
            "Matrix: startup grace discarded an event %.0fs before startup; "
            "events older than the grace window are not processed by this adapter.",
            adapter._startup_ts - event_ts,
        )
        adapter._startup_grace_noted = True
    if adapter._clock_skew_warned or time.time() - adapter._startup_ts <= 30:
        return
    skew = adapter._startup_ts - event_ts
    if not (5 < skew < 86400):  # ignore malformed/absurd timestamps
        return
    if adapter._late_grace_drops and abs(skew - adapter._late_grace_skew) < 60:
        adapter._late_grace_drops += 1
    else:
        adapter._late_grace_skew = skew
        adapter._late_grace_drops = 1
    if adapter._late_grace_drops >= 3:
        logger.warning(
            "Matrix: dropped %d consecutive live events as 'too old' more than 30s after startup "
            "(skew ≈ %.0fs). The host system clock is likely set ahead of real time, which causes "
            "the startup grace filter to silently discard every incoming message. Run "
            "`timedatectl set-ntp true` (or sync NTP) and restart the bot.", adapter._late_grace_drops, skew)
        adapter._clock_skew_warned = True
