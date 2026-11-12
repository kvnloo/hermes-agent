"""tool-context-trim - Z21 (kanban t_01df79f7): cap tool output, dedupe repeat reads.

Two deterministic transforms on the public ``transform_tool_result`` seam (the hook
that runs after ``post_tool_call`` and before the result enters the model's context):

1. **cap+summary** - a *text* result over ``max_chars`` from a non-owner path becomes
   ``head + tail + note``. Tool output was ~52% of Opus weighted tokens, so this is the
   single biggest lever. Single-key content/text/output/stdout JSON string envelopes
   are unwrapped and re-wrapped; other structured results stay exact.
2. **dedupe** - an *identical read-only* call inside one session returns the cached
   result (capped) with a duplicate marker. 14% of tool calls were exact repeats. Any
   non-read tool clears the session cache, so a result can never be replayed after the
   bytes it described changed.

Owner-private paths are never trimmed (they carry Kevin's private data and stay exact);
nothing here touches the network, an LLM, or any credential. Env knobs:
``Z21_TRIM_MAX_CHARS``, ``Z21_TRIM_HEAD``, ``Z21_TRIM_TAIL``, ``Z21_TRIM_DEDUPE_HEAD``,
``Z21_TRIM_OFF=1`` (kill switch), ``Z21_TRIM_OWNER_PATHS`` (colon list, replaces default).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on"}

# Read-only tools only: a repeated read is the same bytes, a repeated write is not.
_READ_TOOLS = frozenset({
    "read_file", "view_file", "list_files", "search_files", "z0_file_search",
    "skill_view", "skills_list", "session_search", "web_search", "web_extract",
    "x_search", "gif_search", "trace_query", "trace_resolve", "todo_list",
})

# Substrings that mean "this arg is about credentials/state - keep it exact".
_SENSITIVE_PARTS = ("auth", "secret", "token", "credential", "password", ".env")

_DEFAULT_OWNER_PATHS = (
    "/mnt/zer0models/sft-svlm",      # Kevin's personal data
    "/mnt/zer0models/data",          # personal data root (ops receipts live here)
    "/home/kvn/.hermes/state",       # session stores
    "/home/kvn/.hermes/profiles",    # profile configs + secrets
    "/home/kvn/.hermes/memories",
    "/home/kvn/.ssh",
    "/home/kvn/.z0int",              # secrets/auth vault dir
    "/home/kvn/.claude",             # Claude auth
    "/home/kvn/.omp",                # omp session data
    "/home/kvn/.config",
    "/home/kvn/.local/share",
)

_CACHE: dict[str, dict[str, str]] = {}
_LOCK = threading.Lock()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _owner_paths() -> tuple[str, ...]:
    raw = os.environ.get("Z21_TRIM_OWNER_PATHS")
    if not raw:
        return _DEFAULT_OWNER_PATHS
    return tuple(p.strip().rstrip("/") for p in raw.split(":") if p.strip())


def _session_cwd(task_id: str) -> str:
    """The session's terminal cwd, best effort (empty for sessions with no shell yet)."""
    try:
        from tools.terminal_tool_lifecycle import get_active_env

        env = get_active_env(task_id)
        return str(getattr(env, "cwd", "") or "")
    except Exception:  # noqa: BLE001 - the hook must never break the tool call
        return ""


def _is_owner_path(args: Any, cwd: str, result_text: str = "") -> bool:
    texts = [cwd]
    if isinstance(args, dict):
        texts += [v for v in args.values() if isinstance(v, str)]
    for text in texts:
        low = text.lower()
        if any(part in low for part in _SENSITIVE_PARTS):
            return True
        for root in _owner_paths():
            if text == root or text.startswith(root + "/"):
                return True
    return (any(part in result_text.lower() for part in _SENSITIVE_PARTS)
            or any(root in result_text for root in _owner_paths()))


def _primary_path(args: Any) -> str:
    if not isinstance(args, dict):
        return ""
    for key in ("path", "file_path", "pattern", "command", "query", "url"):
        value = args.get(key)
        if isinstance(value, str) and value:
            return value[:120]
    return ""


def _is_json_text(text: str) -> bool:
    head = text.lstrip()[:1]
    if head not in ("{", "["):
        return False
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def _trim(text: str, tool_name: str, args: Any, max_chars: int, head: int, tail: int) -> str:
    if len(text) <= max_chars or _is_json_text(text):
        return text
    note = (
        f"\n\n[z21 tool-output trim: {len(text):,} chars -> {head + tail:,}. "
        f"Kept the head {head:,} + tail {tail:,} of a `{tool_name}` result "
        f"({_primary_path(args) or 'no path arg'}). For the omitted middle, re-run the "
        "call with a narrower scope/path or read the specific range.]"
    )
    return text[:head] + note + (text[-tail:] if tail else "")


def _cache_key(tool_name: str, args: Any) -> str:
    try:
        canon = json.dumps(args, sort_keys=True, default=str)
    except (TypeError, ValueError):
        canon = repr(args)
    return f"{tool_name}\x00{canon}"


def _cache_get(session: str, key: str) -> Optional[str]:
    with _LOCK:
        return _CACHE.get(session, {}).get(key)


def _cache_put(session: str, key: str, value: str, max_entries: int = 200, max_bytes: int = 4 << 20) -> None:
    with _LOCK:
        entries = _CACHE.setdefault(session, {})
        entries[key] = value
        while len(entries) > max_entries or sum(len(v) for v in entries.values()) > max_bytes:
            entries.pop(next(iter(entries)))


def _cache_clear(session: str) -> None:
    with _LOCK:
        _CACHE.pop(session, None)


def _on_transform_tool_result(
    tool_name: str = "",
    args: Any = None,
    result: Any = None,
    task_id: str = "",
    session_id: str = "",
    **_: Any,
) -> Optional[str]:
    """Cap oversized non-owner results; replay identical read-only calls. None = unchanged."""
    if os.environ.get("Z21_TRIM_OFF", "").lower() in _TRUTHY:
        return None
    if not isinstance(result, str) or not result:
        return None
    session = session_id or task_id or "default"

    if tool_name not in _READ_TOOLS:
        # Any write/exec/act call can change what a read would return: drop the session cache.
        _cache_clear(session)
        return None

    envelope_key = None
    if _is_json_text(result):
        envelope = json.loads(result)
        if not isinstance(envelope, dict) or envelope.get("_multimodal"):
            return None
        if len(envelope) != 1:
            return None
        envelope_key, text = next(iter(envelope.items()))
        if envelope_key not in {"content", "text", "output", "stdout"} or not isinstance(text, str):
            return None
        result = text
        if _is_json_text(result):
            return None

    # Exempt results must never enter the replay cache, including repeated reads.
    if _is_owner_path(args, _session_cwd(task_id), result):
        return None
    key = _cache_key(tool_name, args)
    cached = _cache_get(session, key)
    if cached is not None:
        head = _int_env("Z21_TRIM_DEDUPE_HEAD", 1600)
        kept = cached[:head]
        marker = (
            f"\n\n[z21 dedupe: identical `{tool_name}` call already ran in this session "
            f"({_primary_path(args) or 'no path arg'}); showing the first {len(kept):,} chars "
            "of the cached result instead of re-reading it. If the file changed since, "
            "make the call differ (e.g. a narrower pattern) or use a different tool.]"
        )
        transformed = kept + marker
    else:
        _cache_put(session, key, result)
        max_chars = _int_env("Z21_TRIM_MAX_CHARS", 4000)
        if len(result) <= max_chars:
            return None
        transformed = _trim(result, tool_name, args, max_chars,
                            _int_env("Z21_TRIM_HEAD", 2400),
                            _int_env("Z21_TRIM_TAIL", 800))
    if envelope_key is not None:
        return json.dumps({envelope_key: transformed}, ensure_ascii=False)
    return transformed


def register(ctx) -> None:
    ctx.register_hook("transform_tool_result", _on_transform_tool_result)
