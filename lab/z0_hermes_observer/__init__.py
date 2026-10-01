"""Observer-only Hermes -> z0intelligence event bridge.

This lab plugin deliberately records metadata, not prompt/tool content.  It is a
measurement substrate for downstream z0 experiments; every callback returns
None and every failure is swallowed so Hermes behavior is unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from hermes_constants import get_hermes_home

PLUGIN_ID = "z0-hermes-observer"
SCHEMA = "z0int.hermes_observer_event.v1"
_LOCK = threading.Lock()

_HOOKS = (
    "on_session_start",
    "pre_llm_call",
    "pre_api_request",
    "post_api_request",
    "api_request_error",
    "pre_auxiliary_call",
    "post_auxiliary_call",
    "pre_tool_call",
    "post_tool_call",
    "subagent_stop",
    "on_session_end",
)

_SCALARS = (
    "task_id", "turn_id", "api_request_id", "session_id", "tool_call_id",
    "platform", "surface", "model", "provider", "api_mode", "aux_task",
    "api_call_count", "retry_count", "max_retries", "message_count",
    "tool_count", "approx_input_tokens", "request_char_count", "max_tokens",
    "api_duration", "duration_ms", "started_at", "ended_at", "status_code",
    "retryable", "reason", "finish_reason", "response_model",
    "assistant_content_chars", "assistant_tool_call_count", "streaming",
    "completed", "failed", "interrupted", "turn_exit_reason",
    "child_role", "child_status", "telemetry_schema_version",
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _event_path() -> Path:
    """Spool file of the active profile: ``<hermes home>/plugin-data/<id>/events.jsonl``.

    Same layout as ``plugins.plugin_storage.plugin_data_dir`` but computed without touching
    the filesystem, so it follows whichever profile is bound to the calling context. A
    profile whose storage cannot be created loses its rows; it never falls back to another
    profile's home.
    """
    override = os.environ.get("Z0INT_HERMES_EVENT_PATH")
    if override:
        return Path(override).expanduser()
    return get_hermes_home() / "plugin-data" / PLUGIN_ID / "events.jsonl"


def _trace_id(payload: Mapping[str, Any]) -> str | None:
    explicit = payload.get("trace_id")
    if explicit:
        return str(explicit)
    session_id = str(payload.get("session_id") or "")
    turn_id = str(payload.get("turn_id") or "")
    if session_id and turn_id:
        return hashlib.sha256((session_id + "\0" + turn_id).encode("utf-8")).hexdigest()
    return session_id or str(payload.get("task_id") or "") or None


def _usage(value: Any) -> dict[str, int | float]:
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, int | float] = {}
    for key, raw in value.items():
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            out[str(key)] = raw
    return out


def _tool_shape(payload: Mapping[str, Any]) -> dict[str, Any]:
    args = payload.get("args")
    result: dict[str, Any] = {
        "tool_name": str(payload.get("tool_name") or ""),
        "arg_keys": sorted(str(k) for k in args) if isinstance(args, Mapping) else [],
    }
    # Never persist raw args/results in v0.  The host already exposes status and
    # bounded error metadata, which are sufficient for the first outcome joins.
    for key in ("status", "error_type", "duration_ms"):
        if payload.get(key) is not None:
            result[key] = payload[key]
    return result


def _subagent_shape(payload: Mapping[str, Any]) -> dict[str, Any]:
    history = payload.get("tool_call_history")
    return {
        "child_role": payload.get("child_role"),
        "child_status": payload.get("child_status"),
        "duration_ms": payload.get("duration_ms"),
        "tool_calls": len(history) if isinstance(history, list) else 0,
    }


def _row(event: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    identity = {
        "harness_id": "hermes",
        "session_id": payload.get("session_id"),
        "task_id": payload.get("task_id"),
        "turn_id": payload.get("turn_id"),
        "trace_id": _trace_id(payload),
        "api_request_id": payload.get("api_request_id"),
        "tool_call_id": payload.get("tool_call_id"),
    }
    data: dict[str, Any] = {
        "schema": SCHEMA,
        "event": event,
        "observed_at": time.time(),
        "identity": identity,
        "fields": {key: payload[key] for key in _SCALARS if payload.get(key) is not None},
    }
    usage = _usage(payload.get("usage"))
    if usage:
        data["usage"] = usage
    if event in {"pre_tool_call", "post_tool_call"}:
        data["tool"] = _tool_shape(payload)
    if event == "subagent_stop":
        data["subagent"] = _subagent_shape(payload)
    if _truthy("Z0INT_HERMES_CAPTURE_SANITIZED_CONTENT"):
        # Explicit opt-in only. Hermes sanitizes these envelopes for secret-key
        # fields, but they may still contain user text, so default is metadata-only.
        if payload.get("request") is not None:
            data["request"] = payload["request"]
        if payload.get("response") is not None:
            data["response"] = payload["response"]
    return data


def _write_row(row: Mapping[str, Any]) -> None:
    encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    path = _event_path()
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")


def observe(event: str, **payload: Any) -> None:
    try:
        _write_row(_row(event, payload))
    except Exception:
        # Observer failures must never affect Hermes execution.
        return None
    return None


def _callback(event: str):
    def callback(**payload: Any) -> None:
        return observe(event, **payload)
    callback.__name__ = f"observe_{event}"
    return callback


_CALLBACKS = {event: _callback(event) for event in _HOOKS}


def register(ctx) -> None:
    for event in _HOOKS:
        ctx.register_hook(event, _CALLBACKS[event])
