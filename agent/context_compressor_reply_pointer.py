"""The gateway's ``[Replying to…: "…"]`` pointer on user turns the compressor restates.

The gateway quotes the message a user replies to (``gateway/inbound_reply_context.py``).
The compressor keeps that quote when it restates an in-flight request, strips it when it
sizes the request, and adds one when the fold removed the reply the request answers
(#144546). Late imports only: ``agent.context_compressor`` imports this module.
"""

from __future__ import annotations

import re
from typing import Any

# Gateway reply pointer prepended to a user turn (gateway/run_inbound.py
# ``_prepend_inbound_reply_context``), optionally behind the Discord triggering note.
# Non-greedy: a quote that itself contains the closing delimiter is only partly
# stripped, which over-counts the request and keeps the conservative anchor.
_GATEWAY_REPLY_POINTER_RE = re.compile(
    r'\A(?:\[Triggering message id: [^\n]*\]\n\n)?'
    r'\[Replying to(?: your previous message| an earlier scheduled cron delivery \([^)\n]*\))?: ".*?"\]\n\n',
    re.DOTALL,
)


def _authored_request_text(content: Any) -> str:
    """Text the user wrote in a turn, without the gateway's reply-to pointer.

    The pointer quotes another message verbatim; it disambiguates which message is being
    answered but is not part of the request, so it must not count toward request size.
    """
    from agent.context_compressor import _restated_request_text

    return _GATEWAY_REPLY_POINTER_RE.sub("", _restated_request_text(content), count=1).strip()


def own_reply_pointer(reply_text: str) -> str:
    """``reply_pointer(reply_text, own_message=True)`` from the gateway, without its cron lookup."""
    from agent.message_sanitization import strip_internal_markup

    return f'[Replying to your previous message: "{strip_internal_markup(reply_text)}"]'


def quote_folded_reply(original: list, inflight: dict, compressed: list, task_text: str) -> str:
    """``task_text`` behind a pointer to the reply it answers, when the fold removed that reply.

    Mid-turn compaction of an over-ceiling turn folds the reply and the request into the
    summary while the tool chain stays (#131412), and the reply anchor cannot put the reply
    back beside a tool-call row. The restated request is then the only verbatim trace of
    that exchange, and "go ahead" without the plan it approves is ambiguous.
    """
    from agent.context_compressor import ContextCompressor, _content_text_for_contains
    from agent.conversation_compression import _is_real_user_message

    if _GATEWAY_REPLY_POINTER_RE.match(task_text) or ContextCompressor._has_merged_inflight_replay(inflight):
        return task_text  # already quotes what it answers, or a carrier restated last cycle
    idx = next((i for i, m in enumerate(original) if m is inflight), 0)
    for message in reversed(original[:idx]):
        if not isinstance(message, dict) or _is_real_user_message(message):
            return task_text
        if message.get("role") != "assistant" or message.get("tool_calls"):
            continue
        if ContextCompressor._is_context_summary_message(message):
            return task_text
        reply = _content_text_for_contains(message.get("content")).strip()
        if not reply:
            continue
        kept = any(
            isinstance(m, dict) and m.get("role") == "assistant"
            and _content_text_for_contains(m.get("content")).strip() == reply
            for m in compressed
        )
        return task_text if kept else f"{own_reply_pointer(reply)}\n\n{task_text}"
    return task_text
