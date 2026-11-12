"""Attention-aware coalescing helpers for Kanban gateway notifications."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Iterable

_SECRET = re.compile(r"(?i)\b(api[_ -]?key|token|password|secret|bearer)\b\s*[:=]\s*\S+")
_SECURITY = re.compile(r"(?i)\b(security|trust|privileg|sudo|credential|auth(?:entication|orization)?|secret|token)\b")
_NO_ACTION = re.compile(r"(?i)\b(focus[- ]?pause|deliberate(?:ly)? parked|duplicate|superseded|no[- ]?action)\b")
_SIGNOFF = re.compile(r"(?i)\b(captain|operator|human)\b.{0,40}\b(sign[- ]?off|approve|decision|action required)\b")
_EMERGENCY = re.compile(r"(?i)\b(expir(?:e|es|ing|y)|deadline|safety|emergency|irreversible)\b")


@dataclass(frozen=True)
class AttentionPolicy:
    enabled: bool = False
    mode: str = "pm"
    interval_seconds: int = 900
    max_chars: int = 900
    destinations: tuple[dict[str, str], ...] = ()
    focus_task_ids: tuple[str, ...] = ()


def load_attention_policy(config: Any) -> AttentionPolicy:
    raw = ((config or {}).get("kanban") or {}).get("notification_policy") or {}
    destinations = raw.get("destinations") or []
    if isinstance(destinations, dict):
        destinations = [destinations[key] for key in sorted(destinations)]
    clean_rows = []
    required = {"profile", "platform", "chat_id", "chat_type"}
    allowed = required | {"thread_id"}
    for item in destinations:
        if not isinstance(item, dict):
            raise ValueError("notification destination must be a mapping")
        if set(item) - allowed or not required.issubset(item):
            raise ValueError(
                "notification destination requires exact profile, platform, chat_id, and chat_type"
            )
        row = {k: str(v).strip() for k, v in item.items()}
        if any(not row[k] for k in required) or ("thread_id" in row and not row["thread_id"]):
            raise ValueError("notification destination identity fields cannot be empty")
        row["platform"] = row["platform"].lower()
        row["chat_type"] = row["chat_type"].lower()
        clean_rows.append(row)
    clean = tuple(clean_rows)
    mode = str(raw.get("mode", "pm") or "pm").lower()
    if mode not in {"brainstorm", "pm", "copilot"}:
        mode = "pm"
    focus = raw.get("focus_task_ids") or []
    if isinstance(focus, dict):
        focus = [focus[key] for key in sorted(focus)]
    if not isinstance(focus, list):
        focus = []
    return AttentionPolicy(
        enabled=bool(raw.get("enabled", False)),
        mode=mode,
        interval_seconds=max(5, int(raw.get("interval_seconds", 900) or 900)),
        max_chars=max(160, int(raw.get("max_chars", 900) or 900)),
        destinations=clean,
        focus_task_ids=tuple(str(v) for v in focus[:3]),
    )


def applies(policy: AttentionPolicy, sub: dict[str, Any]) -> bool:
    if not policy.enabled:
        return False
    metadata = sub.get("delivery_metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    actual = {
        "profile": str(sub.get("notifier_profile") or ""),
        "platform": str(sub.get("platform") or "").lower(),
        "chat_id": str(sub.get("chat_id") or ""),
        "thread_id": str(sub.get("thread_id") or ""),
        "chat_type": str(sub.get("chat_type") or metadata.get("chat_type") or "dm").lower(),
    }
    return any(rule and all(actual.get(k) == v for k, v in rule.items()) for rule in policy.destinations)


def for_destination(policy: AttentionPolicy, sub: dict[str, Any]) -> AttentionPolicy:
    """Overlay exact conversation state without changing policy activation."""
    if not applies(policy, sub):
        return policy
    try:
        from gateway.config import Platform
        from gateway.conversation_modes import get_mode
        from gateway.session import SessionSource

        metadata = sub.get("delivery_metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        source = SessionSource(
            platform=Platform(str(sub.get("platform") or "").lower()),
            chat_id=str(sub.get("chat_id") or ""),
            chat_type=str(sub.get("chat_type") or metadata.get("chat_type") or "dm"),
            thread_id=sub.get("thread_id") or None,
            profile=sub.get("notifier_profile") or None,
        )
        state = get_mode(source)
        return replace(policy, mode=state.mode, focus_task_ids=state.focus)
    except Exception:
        return policy


def is_urgent(kind: str, payload: Any, task: Any = None, mode: str = "pm") -> bool:
    payload = payload if isinstance(payload, dict) else {}
    text = " ".join(str(payload.get(k) or "") for k in ("reason", "error", "summary"))
    block_kind = str(payload.get("kind") or getattr(task, "block_kind", "") or "")
    if _SECURITY.search(text):
        return True
    if kind in {"completed", "review_requested"} and _SIGNOFF.search(text):
        return True
    if kind == "blocked":
        if _NO_ACTION.search(text):
            return False
        if mode == "brainstorm" and not _EMERGENCY.search(text):
            return False
        return block_kind in {"needs_input", "capability"}
    return kind in {"gave_up", "block_loop_detected", "changes_requested"}


def redact(text: str) -> str:
    return _SECRET.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)


def render_digest(items: Iterable[dict[str, Any]], max_chars: int = 900) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, int]] = set()
    for item in items:
        key = (str(item.get("task_id")), int(item.get("event_id") or 0))
        if key in seen:
            continue
        seen.add(key)
        family = str(item.get("parent_id") or item.get("task_id") or "other")
        grouped.setdefault(family, []).append(item)
    lines = ["Kanban digest — routine updates"]
    for family, rows in grouped.items():
        counts: dict[str, int] = {}
        ids: list[str] = []
        for row in rows:
            kind = str(row.get("kind") or "updated")
            counts[kind] = counts.get(kind, 0) + 1
            tid = str(row.get("task_id") or "")
            if tid and tid not in ids:
                ids.append(tid)
        summary = ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))
        line = redact(f"• {family}: {summary} — {', '.join(ids[:6])}")
        if len("\n".join(lines + [line])) > max_chars:
            remaining = sum(len(v) for v in grouped.values()) - sum(len(grouped[k]) for k in list(grouped)[:len(lines)-1])
            suffix = f"• … {max(1, remaining)} more update(s); use kanban status for drill-down"
            if len("\n".join(lines + [suffix])) <= max_chars:
                lines.append(suffix)
            break
        lines.append(line)
    return "\n".join(lines)[:max_chars]
