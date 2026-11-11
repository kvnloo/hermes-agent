"""Consumer seam for z0's burn_pace law (z0 repo: bend/burn_pace, lib/z0/burn_pace.py).

Loads the deployed z0 twin from ~/.local/lib/z0/burn_pace/current/burn_pace.py (override:
HERMES_POOL_ADMISSION) and asks it which pool rows may serve. Hermes supplies only the facts it
owns: provider, rows, requested model and the profile the turn runs for. If the twin cannot be
loaded the pool is returned unchanged and an ERROR is logged (external gate fails open).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

logger = logging.getLogger(__name__)
_DEFAULT = Path.home() / ".local/lib/z0/burn_pace/current/burn_pace.py"
_mod = {"path": None, "mtime": None, "module": None}
_session = ContextVar("burn_pace_session", default=None)


def _cache_breaks_path():
    return Path.home() / ".z0int/state/posture/cache-breaks.jsonl"


@contextmanager
def cache_session(agent):
    """Bind admission to this conversation, including context-copied request workers."""
    if agent.provider == "anthropic":
        try:
            path = _cache_breaks_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
        except OSError:
            logger.exception("cache-break log could not be initialized")
    token = _session.set(agent)
    try:
        yield
    finally:
        _session.reset(token)


def _credential_tag(key):
    # Receipts must never contain API keys or OAuth tokens.
    return hashlib.sha256(key.encode()).hexdigest()[:16] if isinstance(key, str) and key else None


def record_call(agent, response, messages):
    if agent.provider != "anthropic" or not getattr(response, "usage", None):
        return
    from agent.usage_pricing import normalize_usage

    usage = normalize_usage(response.usage, provider=agent.provider, api_mode=agent.api_mode)
    current = {
        "ts": time.time(), "session": agent.session_id, "in": usage.prompt_tokens,
        "cred": _credential_tag(getattr(agent, "_anthropic_api_key", None) or getattr(agent, "api_key", None)),
        "msgs": len(messages),
    }
    previous = getattr(agent, "_cache_last_call", None)
    agent._cache_last_call = current
    if not previous or previous["session"] != current["session"]:
        return
    gap = current["ts"] - previous["ts"]
    if 0 <= gap < 270 and usage.cache_read_tokens < 0.5 * previous["in"]:
        receipt = dict(current, gap_s=gap, prev_in=previous["in"],
                       cache_read=usage.cache_read_tokens, write=usage.cache_write_tokens,
                       cred_prev=previous["cred"], msgs_prev=previous["msgs"])
        try:
            with _cache_breaks_path().open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(receipt) + "\n")
        except OSError:
            logger.exception("cache-break receipt could not be written")


def _warm_entry(twin, provider, entries):
    agent = _session.get()
    previous = getattr(agent, "_cache_last_call", None)
    if (provider != "anthropic" or not previous or previous["session"] != agent.session_id
            or not previous["cred"] or not 0 <= time.time() - previous["ts"] < 300):
        return None
    entry = next((e for e in entries if _credential_tag(e.runtime_api_key) == previous["cred"]), None)
    if entry is None or getattr(entry, "last_status", None) in {"exhausted", "dead"}:
        return None
    lanes, reading = twin._load()
    lane = (lanes.get(provider) or {}).get(entry.label)
    if lane:
        fresh, used, _pace, _why = twin.classify(lane, reading)
        if fresh != twin.FRESH or used != twin.UNDER:
            return None
    return entry


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
    warm = _warm_entry(twin, provider, entries)
    return [warm] if warm is not None else twin.admit(provider, entries, model, profile)
