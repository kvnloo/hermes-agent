"""Persistent, destination-scoped attention modes for gateway conversations.

Modes affect presentation and notification delivery only.  They deliberately do
not touch agents, tools, tasks, workers, scheduling, or authorization state.
"""
from __future__ import annotations

import contextlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from utils import atomic_json_write

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX
    msvcrt = None

_SCHEMA_VERSION = 1
_MAX_FOCUS = 3
_VALID_MODES = frozenset({"pm", "brainstorm", "copilot"})
_process_lock = threading.RLock()


@contextlib.contextmanager
def _mutation_lock(target: Path):
    """Serialize the complete profile-wide read/modify/write transaction."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with _process_lock:
        handle = open(target.with_name(f".{target.name}.lock"), "a+b")
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:  # pragma: no cover - Windows
                handle.seek(0)
                if handle.read(1) == b"":
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                getattr(msvcrt, "locking")(handle.fileno(), getattr(msvcrt, "LK_LOCK"), 1)
            yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:  # pragma: no cover - Windows
                    handle.seek(0)
                    getattr(msvcrt, "locking")(handle.fileno(), getattr(msvcrt, "LK_UNLCK"), 1)
            finally:
                handle.close()


@dataclass(frozen=True)
class ConversationMode:
    mode: str = "pm"
    focus: tuple[str, ...] = ()


def conversation_key(source: Any) -> str:
    """Exact profile/platform/chat/thread identity; groups never inherit DMs."""
    platform = getattr(getattr(source, "platform", None), "value", None) or getattr(source, "platform", "")
    parts = (
        str(getattr(source, "profile", None) or "default"),
        str(platform).lower(),
        str(getattr(source, "chat_type", None) or "dm").lower(),
        str(getattr(source, "chat_id", None) or ""),
        str(getattr(source, "thread_id", None) or ""),
    )
    return "\x1f".join(parts)


def _path() -> Path:
    return get_hermes_home() / "gateway" / "conversation_modes.json"


def _load(path: Path | None = None) -> dict[str, Any]:
    target = path or _path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("version") != _SCHEMA_VERSION:
            return {"version": _SCHEMA_VERSION, "conversations": {}}
        if not isinstance(raw.get("conversations"), dict):
            return {"version": _SCHEMA_VERSION, "conversations": {}}
        return raw
    except (OSError, ValueError, TypeError):
        return {"version": _SCHEMA_VERSION, "conversations": {}}


def get_mode(source: Any, *, path: Path | None = None) -> ConversationMode:
    row = _load(path)["conversations"].get(conversation_key(source), {})
    mode = str(row.get("mode") or "pm").lower() if isinstance(row, dict) else "pm"
    if mode not in _VALID_MODES:
        mode = "pm"
    focus = row.get("focus", []) if isinstance(row, dict) else []
    if not isinstance(focus, list):
        focus = []
    return ConversationMode(mode, tuple(str(v) for v in focus[:_MAX_FOCUS] if str(v).strip()))


def set_mode(source: Any, mode: str, *, focus: list[str] | None = None, path: Path | None = None) -> ConversationMode:
    normalized = str(mode).strip().lower()
    if normalized == "manager":
        normalized = "pm"
    if normalized not in _VALID_MODES:
        raise ValueError("unknown conversation mode")
    target = path or _path()
    with _mutation_lock(target):
        data = _load(target)
        row = data["conversations"].get(conversation_key(source), {})
        previous_focus = row.get("focus", []) if isinstance(row, dict) else []
        chosen = tuple(str(v) for v in previous_focus[:_MAX_FOCUS] if str(v).strip()) if focus is None else tuple(dict.fromkeys(str(v).strip() for v in focus if str(v).strip()))[:_MAX_FOCUS]
        data["conversations"][conversation_key(source)] = {"mode": normalized, "focus": list(chosen)}
        atomic_json_write(target, data, mode=0o600)
    return ConversationMode(normalized, tuple(chosen))


def set_focus(source: Any, values: list[str], *, path: Path | None = None) -> ConversationMode:
    return set_mode(source, get_mode(source, path=path).mode, focus=values, path=path)


def receipt(state: ConversationMode) -> str:
    if state.mode == "brainstorm":
        return "BRAINSTORM · direct replies only · updates queued"
    if state.mode == "copilot":
        scope = ", ".join(state.focus) if state.focus else "no focus set"
        return f"COPILOT · focused on {scope} · execution remains canonical"
    return "PM · portfolio milestones · routine updates digested"
