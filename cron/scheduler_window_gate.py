"""Tick gate: due jobs that declare a decision window fire only while it is open.

Jobs with neither ``window_class`` nor ``stale_after_s`` pass straight through, and the window
provider is not even resolved, so a store without opted-in jobs ticks exactly as before.

For the rest, ``cron.decision_window.gate`` decides. A held job is skipped like a headless tick
skips agent jobs (``cron.scheduler_gateway_gate``): no run is recorded, the due instant does not
move, the dispatch marks the scan wrote are dropped and ``last_fire_error`` carries the reason, so
a later tick fires it once the window opens (within the job's catch-up window; past it the due
scan's ordinary missed-run policy applies). A stale recurring occurrence is dropped instead: the
job advances to its next slot, because a late proactive message is noise.
"""
import logging

from cron.decision_window import ALWAYS_ANYTIME, WindowProvider, gate, is_stale

logger = logging.getLogger(__name__)


def resolve_window_provider() -> WindowProvider:
    """The window provider for this tick; every window is open until one is registered."""
    return ALWAYS_ANYTIME


def _opted_in(job: dict) -> bool:
    return job.get("window_class") is not None or job.get("stale_after_s") is not None


def hold_outside_window(due_jobs: list) -> list:
    """Return the due jobs whose window is open; hold or drop the others (see module doc)."""
    from cron.jobs import _hermes_now, advance_next_runs
    from cron.scheduler_gateway_gate import _note_fire_refused

    gated = [job for job in due_jobs if _opted_in(job)]
    if not gated:
        return due_jobs
    provider = resolve_window_provider()
    now = _hermes_now()
    held: dict[str, str] = {}
    for job in gated:
        fire, reason = gate(job, now, provider)
        if not fire:
            held[str(job["id"])] = reason
    if not held:
        return due_jobs
    by_reason: dict[str, list[str]] = {}
    for job_id, reason in held.items():
        by_reason.setdefault(reason, []).append(job_id)
    for reason, job_ids in by_reason.items():
        _note_fire_refused(job_ids, f"Held: {reason}")
    advance_next_runs([str(job["id"]) for job in gated if str(job["id"]) in held and is_stale(job, now)])
    logger.debug("Cron tick held %d job(s) outside their decision window: %s", len(held),
                 "; ".join(f"{job_id}: {reason}" for job_id, reason in held.items()))
    return [job for job in due_jobs if str(job["id"]) not in held]
