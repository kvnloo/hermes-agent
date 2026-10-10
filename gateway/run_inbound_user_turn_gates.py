"""User-turn gates for the fresh-turn path of ``_handle_message``.

Refusals that apply only to a message a user sent, checked after the idle commands have been
dispatched and before the session slot is claimed. Internal wakes and completions skip them.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Tuple

from agent.i18n import t

# Log-record parity with the origin module.
logger = logging.getLogger("gateway.run")


async def user_turn_gate(runner: Any, source: Any, session_key: str) -> Tuple[bool, Optional[str]]:
    """Return ``(gated, reply)``; ``gated=False`` means the user's fresh turn may start."""
    if await asyncio.to_thread(runner._is_telegram_topic_root_lobby, source):
        # Debounced so a user who forgets about topic mode doesn't get ten reminders.
        if runner._should_send_telegram_lobby_reminder(source):
            return True, runner._telegram_topic_root_lobby_message()
        return True, None
    # External-drain new-turn gate: when NAS engaged an external drain (.drain_request.json,
    # seen by _drain_control_watcher), refuse to START new turns so the in-flight set can
    # only fall to zero. Reversible.
    if runner._external_drain_active:
        logger.info("Refusing new turn for session %s — external drain active.", session_key)
        return True, t("gateway.busy.draining_maintenance")
    return False, None
