"""Editable progress-bubble state and refusal handling for the turn runner."""

from __future__ import annotations

import dataclasses
import logging
import time
from typing import Any

logger = logging.getLogger("gateway.run")

# Minimum seconds between progress edits (Telegram flood control).
PROGRESS_EDIT_INTERVAL = 1.5


@dataclasses.dataclass
class ProgressEditState:
    """Mutable editable-bubble state shared by ``send_progress_messages`` and its helpers."""
    adapter: Any
    progress_lines: list
    progress_msg_id: Any
    can_edit: bool
    _progress_len_fn: Any
    _PROGRESS_TEXT_LIMIT: int
    _edit_accepts_metadata: bool
    # A permanent edit failure already moved progress to a fresh bubble that has not yet been
    # edited successfully. A second failure in a row means edits are unusable, not one dead bubble.
    reanchored: bool = False
    # Monotonic deadline set by a flood refusal. Until it passes, new lines are only buffered:
    # no edit, split, or send, so a refused bubble is not retried once per incoming tool line.
    defer_until: float = 0.0


def is_flood_refusal(result) -> bool:
    error = (getattr(result, "error", "") or "").lower()
    return getattr(result, "retry_after", None) is not None or any(w in error for w in ("flood", "retry after"))


def edit_failure_is_deferrable(st, result) -> bool:
    """Transient and rate-limit edit failures leave the bubble editable for a later tick.

    A flood refusal says "not now", not "never": disabling edits on it turns every later tool
    line into its own message for the rest of the turn, and sending one now spends the budget
    the platform just said is exhausted.
    """
    if is_flood_refusal(result):
        wait = max(float(getattr(result, "retry_after", None) or 0.0), PROGRESS_EDIT_INTERVAL)
        st.defer_until = time.monotonic() + wait
        logger.info("[%s] Progress edit flood control, deferring edits for %.1fs", st.adapter.name, wait)
        return True
    if getattr(result, "retryable", False):
        logger.debug("[%s] Transient progress edit failure, retrying next tick", st.adapter.name)
        return True
    return False


def progress_deferred(st) -> bool:
    return time.monotonic() < st.defer_until


def abandon_progress_bubble(st) -> bool:
    """After a permanent edit failure, continue in a fresh bubble (True) unless the previous
    fresh bubble also failed, which means editing itself is unusable (False, can_edit off)."""
    if st.reanchored:
        st.can_edit = False
        return False
    logger.info("[%s] Progress bubble no longer editable, starting a fresh one", st.adapter.name)
    st.reanchored = True
    st.progress_msg_id = None
    return True


def progress_text(lines: list) -> str:
    return "\n".join(str(line) for line in lines)
