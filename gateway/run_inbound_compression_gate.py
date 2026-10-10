"""Compression new-turn gate for the fresh-turn path of ``_handle_message`` (#134239).

A post-turn compression starts ~0.4 s after "Turn ended", i.e. while ``_is_session_running`` is
already False, so a follow-up message reaches the fresh-turn path with the guard from #56391 never
firing. The turn it starts reads the pre-rotation history and its own post-turn compression later
commits a snapshot taken before the previous commit — double-compressing the transcript. The
running-agent path already demotes for this; the fresh-turn path must hold the turn back too. The
lock is TTL-leased (~300 s), so a leaked lock can't wedge this.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from agent.i18n import t

# Log-record parity with the origin module.
logger = logging.getLogger("gateway.run")


async def compression_gate(
    runner: Any, event: Any, source: Any, session_key: str, is_internal: bool
) -> Tuple[bool, Optional[str]]:
    """Return ``(gated, reply)``; ``gated=False`` means the fresh turn may start."""
    if not await runner._session_has_compression_in_flight(session_key):
        return False, None
    if not is_internal:
        logger.info("Refusing new turn for session %s — context compression in flight.", session_key)
        return True, t("gateway.busy.compressing_retry")
    # Internal wakes/completions are not user-resendable. Put the exact event back through the
    # adapter FIFO instead of starting it on the pre-compression transcript. BasePlatformAdapter's
    # identical-event drain backoff prevents a hot loop while the lock remains held and preserves
    # the event's routing/security metadata until the committed transcript is visible.
    adapter = runner._delivery_adapter_for(source)
    if adapter is None:
        logger.error(
            "Could not defer internal turn for session %s during compression — "
            "delivery adapter unavailable.",
            session_key,
        )
        return True, None
    runner._enqueue_fifo(session_key, event, adapter)
    logger.info("Deferring internal turn for session %s — context compression in flight.", session_key)
    return True, None
