"""Consumer seam for z0's burn_pace law (z0 repo: bend/burn_pace, lib/z0/burn_pace.py).

Loads the deployed z0 twin from ~/.local/lib/z0/burn_pace/current/burn_pace.py (override:
HERMES_POOL_ADMISSION) and asks it which pool rows may serve. Hermes supplies only the facts it
owns: provider, rows, requested model and the profile the turn runs for. If the twin cannot be
loaded the pool is returned unchanged and an ERROR is logged (external gate fails open).
"""
from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
_DEFAULT = Path.home() / ".local/lib/z0/burn_pace/current/burn_pace.py"
_mod = {"path": None, "mtime": None, "module": None}


def _twin():
    path = Path(os.environ.get("HERMES_POOL_ADMISSION") or _DEFAULT)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    if _mod["path"] != path or _mod["mtime"] != mtime:
        spec = importlib.util.spec_from_file_location("z0_burn_pace", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _mod.update(path=path, mtime=mtime, module=module)
    return _mod["module"]


def admit(provider: str, entries: list, model=None) -> list:
    if not entries:
        return entries
    try:
        twin = _twin()
    except Exception:
        logger.exception("burn-pace: z0 twin failed to load; pool unchanged")
        return entries
    if twin is None:
        logger.error("burn-pace: z0 twin missing at %s; pool unchanged", _DEFAULT)
        return entries
    try:
        from hermes_cli.profiles import current_profile_name
        profile = current_profile_name()
    except Exception:
        profile = None
    return twin.admit(provider, entries, model, profile)
