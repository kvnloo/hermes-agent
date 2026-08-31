"""Deterministic retained tool-result attention accounting."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS = 400_000


def _content_chars(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(part.get("text", ""))
            for part in content
            if isinstance(part, Mapping) and isinstance(part.get("text"), str)
        )
    return len(str(content)) if content is not None else 0


def retained_tool_result_chars(history: Iterable[Mapping[str, Any]]) -> int:
    """Return replayable characters carried by persisted tool-result rows."""
    return sum(
        _content_chars(message.get("content"))
        for message in history
        if isinstance(message, Mapping) and message.get("role") == "tool"
    )


def telegram_history_exceeds_attention_budget(
    history: Iterable[Mapping[str, Any]],
    *,
    budget_chars: int = DEFAULT_TELEGRAM_TOOL_RESULT_BUDGET_CHARS,
) -> bool:
    """Whether a Telegram request must compact or stop before provider replay."""
    if budget_chars < 0:
        raise ValueError("budget_chars must be non-negative")
    return retained_tool_result_chars(history) > budget_chars
