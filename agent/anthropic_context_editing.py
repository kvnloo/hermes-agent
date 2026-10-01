"""Opt-in Anthropic server-side context editing on the native Messages API (#526).

With ``compression.anthropic_context_editing: true`` the main-turn request carries
``context_management={"edits": [{"type": "clear_tool_uses_20250919", ...}]}`` (beta
``context-management-2025-06-27``, attached in ``build_anthropic_kwargs``), and the API clears the
oldest tool results server-side once the prompt crosses ``trigger``. The client keeps the full
transcript, and on preserved-thinking models a server-side clear is not a history edit (a
client-side prune is).

It manages the context window; it does not save money. Each clear rewrites the cached prefix
from the first cleared result onward, so the trigger sits just under the local compressor's
(the server goes first) and ``clear_at_least`` keeps clears large and rare. The local compressor
stays enabled, but it keys on the provider-reported prompt size, which after a clear is the
post-clear size, so it fires later while the resent transcript keeps growing. Same gate shape
as ``agent/native_compaction.py``: opt-in, re-checked per request, disabled for the session by
a structured 400 (``agent/turn_recovery.py``). Native Anthropic API and Claude models only;
``clear_thinking_20251015`` is not sent.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agent.anthropic_endpoints import _is_third_party_anthropic_endpoint
from agent.native_compaction import resolve_compact_threshold

# A clear must free at least this share of the trigger; otherwise the server skips it and the
# local compressor handles the session at its usual threshold.
CLEAR_AT_LEAST_FRACTION = 0.2


def anthropic_context_management(agent: Any) -> Optional[Dict[str, Any]]:
    """Return the ``context_management`` payload for this ``anthropic_messages`` request, or None
    ("do not send"). Called only from that wire's kwargs builder."""
    # compression.enabled: false disables ALL automatic compaction, server-side included.
    if not getattr(agent, "anthropic_context_editing", False) or not getattr(agent, "compression_enabled", True):
        return None
    # A server-side clear is a lossy boundary no pre-compress checkpoint can precede.
    if getattr(agent, "compression_checkpoint_required", False) is True:
        return None
    if "claude" not in str(getattr(agent, "model", None) or "").lower():
        return None
    # Third-party Messages endpoints (Bedrock, Azure, Portal, MiniMax, proxies) never see the field.
    if _is_third_party_anthropic_endpoint(getattr(agent, "_anthropic_base_url", None)):
        return None
    compressor = getattr(agent, "context_compressor", None)
    trigger = resolve_compact_threshold(None, getattr(compressor, "threshold_tokens", None))
    return {"edits": [{
        "type": "clear_tool_uses_20250919",
        "trigger": {"type": "input_tokens", "value": trigger},
        "clear_at_least": {"type": "input_tokens", "value": int(trigger * CLEAR_AT_LEAST_FRACTION)},
    }]}
