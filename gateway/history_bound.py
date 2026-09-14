"""Deterministic no-LLM transcript window for gateway turns.

LLM session hygiene is an availability-bound best effort: when the 10s turn-hold
expires, compression cooldown is active, or Codex compaction does not shrink
the mirror, the turn previously proceeded on the full uncompressed transcript.
That is the Telegram context-rot path — mixed tasks stay in context until the
model hallucinates.

This bound is applied on every inbound after hygiene returns, including the
skip/timeout/cooldown paths. It does not delete stored history.
"""

from __future__ import annotations

from typing import Any, List, Mapping, MutableMapping, Sequence

_BOUNDARY_PREFIX = "[CONTEXT BOUNDARY]"


def bound_history_to_hard_limit(
    history: Sequence[Mapping[str, Any]] | None,
    hard_msg_limit: int,
    protect_first_n: int = 3,
) -> List[MutableMapping[str, Any]] | Sequence[Mapping[str, Any]] | None:
    """Keep at most ``hard_msg_limit`` messages for the model context.

    Preserves the opening ``protect_first_n`` messages and the newest tail,
    inserting one boundary stub so the model knows context was omitted.
    No-ops return the input object.
    """
    if not history or hard_msg_limit <= 0 or len(history) <= hard_msg_limit:
        return history
    protect_first_n = max(0, min(int(protect_first_n), hard_msg_limit - 1))
    tail_n = hard_msg_limit - protect_first_n - 1
    if tail_n < 1:
        return list(history[-hard_msg_limit:])
    dropped = len(history) - protect_first_n - tail_n
    stub: MutableMapping[str, Any] = {
        "role": "assistant",
        "content": (
            f"{_BOUNDARY_PREFIX} Omitted {dropped} earlier messages from this "
            "turn's model context so the session stays bounded. Do not invent "
            "details from omitted turns. Full history remains stored."
        ),
    }
    head = list(history[:protect_first_n])
    tail = list(history[-tail_n:])
    return head + [stub] + tail
