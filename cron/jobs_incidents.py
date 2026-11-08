"""Best-effort bridge from job lifecycle changes to the durable incident ledger."""

import logging

logger = logging.getLogger(__name__)


def retire_job_incidents(job_id: str) -> None:
    """Never block an operator pause/removal on an incident DB failure."""
    try:
        from cron.incidents import orphan_incidents_for_unrunnable_job

        orphan_incidents_for_unrunnable_job(job_id)
    except Exception:
        logger.debug("Could not retire incidents for job %s", job_id, exc_info=True)
