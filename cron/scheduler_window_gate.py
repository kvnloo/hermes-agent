"""Tick gate: due jobs that declare a decision window fire only while it is open.

Jobs with neither ``window_class`` nor ``stale_after_s`` pass straight through, and the window
provider is not even resolved, so a store without opted-in jobs ticks exactly as before.

For the rest, ``cron.decision_window.gate`` decides. A held job is skipped like a headless tick
skips agent jobs (``cron.scheduler_gateway_gate``): no run is recorded, the due instant does not
move, the dispatch marks the scan wrote are dropped and ``last_fire_error`` carries the reason, so
a later tick fires it once the window opens (within the job's catch-up window; past it the due
scan's ordinary missed-run policy applies). A stale occurrence is dropped instead: the job advances
to its next slot, because a late proactive message is noise. Both fields need a recurring
schedule (``cron.decision_window.validate_window_knobs``).
"""
import logging

from cron.decision_window import ALWAYS_ANYTIME, WindowProvider, gate, is_stale

logger = logging.getLogger(__name__)


def resolve_window_provider() -> WindowProvider:
    """The provider a plugin registered for this profile (``ctx.register_window_provider``), else
    ``ALWAYS_ANYTIME``: every window open."""
    from hermes_cli.plugins import get_plugin_window_provider

    return get_plugin_window_provider() or ALWAYS_ANYTIME


def _opted_in(job: dict) -> bool:
    return job.get("window_class") is not None or job.get("stale_after_s") is not None


WINDOW_HOLD = "window_hold"  # ``last_fire_error["kind"]``: ``hermes cron list`` explains a hold, not an outage


def _note_held(held: dict[str, str]) -> None:
    """Stamp each held job's reason and drop the dispatch marks the due scan just wrote: the slot
    was never handed over, so nothing must "restore" or "reclaim" it."""
    from cron.jobs import _hermes_now, _jobs_lock, load_jobs, save_jobs

    at = _hermes_now().isoformat()
    with _jobs_lock():
        jobs = load_jobs()
        for job in jobs:
            reason = held.get(str(job["id"]))
            if reason is None:
                continue
            job["last_fire_error"] = {"at": at, "detail": reason[:500], "kind": WINDOW_HOLD}
            job.pop("pending_slot", None)
            if job.get("run_claim") is not None:
                job["run_claim"] = None
        save_jobs(jobs)


def hold_outside_window(due_jobs: list) -> list:
    """Return the due jobs whose window is open; hold or drop the others (see module doc)."""
    from cron.jobs import _hermes_now, advance_next_runs

    gated = [job for job in due_jobs if _opted_in(job)]
    if not gated:
        return due_jobs
    provider = resolve_window_provider()
    now = _hermes_now()
    held: dict[str, str] = {}
    stale: list[str] = []
    for job in gated:
        fire, reason = gate(job, now, provider)
        if fire:
            continue
        if is_stale(job, now):
            stale.append(str(job["id"]))
            held[str(job["id"])] = f"Dropped: {reason}; the job moved to its next slot"
        else:
            held[str(job["id"])] = f"Held: {reason}; it fires once the window opens"
    if not held:
        return due_jobs
    _note_held(held)
    advance_next_runs(stale)
    logger.debug("Cron tick held %d job(s) outside their decision window: %s", len(held),
                 "; ".join(f"{job_id}: {reason}" for job_id, reason in held.items()))
    return [job for job in due_jobs if str(job["id"]) not in held]
