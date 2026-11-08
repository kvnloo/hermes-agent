"""Keep managed browsers alive while a vault page operation waits for a human.

This inhibits only inactivity cleanup, not explicit close, provider expiry or profile changes.
Retention follows existing session records; it neither creates a browser nor pins a CDP target.
"""

from __future__ import annotations

from contextlib import contextmanager

from hermes_constants import hermes_home_key


class VaultBrowserClosing(RuntimeError):
    """The inactivity janitor already claimed this browser."""


def _records_for_vault(task_id, home, endpoint):
    from tools import browser_session as bs

    owned = [(key, info) for key, info in bs._active_sessions.items()
             if (info.get("home_key") or bs._session_owner_homes.get(key)) == home]
    if endpoint:
        return [(key, info) for key, info in owned if info.get("cdp_url") == endpoint]
    exact = [(key, info) for key, info in owned if key == task_id]
    if exact:
        return exact
    return [(key, info) for key, info in owned
            if bs.owner_task_id(key) == task_id and not bs.is_local_sidecar_key(key)]


@contextmanager
def retain_vault_browser(task_id):
    """Retain only this home's existing browser records through inspection, prompt and fill."""
    from tools import browser_session as bs, browser_session_lifecycle as lifecycle
    from tools.browser_supervisor import SUPERVISOR_REGISTRY

    home, task = hermes_home_key(), task_id or "default"
    supervisor = SUPERVISOR_REGISTRY.get(task, home_key=home)
    endpoint = supervisor.cdp_url if supervisor else None
    with bs._cleanup_lock:
        records = _records_for_vault(task, home, endpoint)
        if any(info.get("_idle_cleanup") for _, info in records):
            raise VaultBrowserClosing("The browser is closing after inactivity; reopen the page and retry.")
        for _, info in records:
            info["_vault_holds"] = info.get("_vault_holds", 0) + 1
    try:
        yield
    finally:
        with bs._cleanup_lock:
            for key, info in records:
                count = info["_vault_holds"] - 1
                if count:
                    info["_vault_holds"] = count
                else:
                    info.pop("_vault_holds")
                # Explicit cleanup/replacement wins. Never resurrect or touch its successor.
                if bs._active_sessions.get(key) is info and key in bs._session_last_activity:
                    bs._session_last_activity[key] = lifecycle.time.time()
