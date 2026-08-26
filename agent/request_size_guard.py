"""Provider-neutral outbound request-body size guard.

The guard runs on the final SDK kwargs immediately before transport. It keeps
ordinary requests byte-stable, spills oversized textual tool results to the
profile-scoped spillover cache, and refuses to open the network when the body
still exceeds the hard safety budget.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import logging
from typing import Any, Iterator

from tools.tool_result_storage import (
    PERSISTED_OUTPUT_TAG,
    _build_persisted_message,
    _write_to_spillover,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_REQUEST_BODY_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_INLINE_TOOL_CHARS = 100_000
_HEAD_FRACTION = 0.6


class RequestBodyTooLarge(RuntimeError):
    """Raised before transport when safe compaction cannot bound a request."""


@dataclass(frozen=True)
class RequestSizeReport:
    before_bytes: int
    after_bytes: int
    compacted_tool_results: int
    reason: str


def _serialized_body_bytes(payload: dict[str, Any]) -> int:
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8", errors="replace")
    )


def _tool_output_slots(payload: dict[str, Any]) -> Iterator[tuple[dict, str, str]]:
    """Yield (container, field, stable id) for provider tool-result strings."""
    messages = payload.get("messages")
    if isinstance(messages, list):
        for index, message in enumerate(messages):
            if not isinstance(message, dict) or message.get("role") != "tool":
                continue
            if isinstance(message.get("content"), str):
                yield message, "content", str(message.get("tool_call_id") or f"chat_{index}")

    response_input = payload.get("input")
    if isinstance(response_input, list):
        for index, item in enumerate(response_input):
            if not isinstance(item, dict) or item.get("type") != "function_call_output":
                continue
            if isinstance(item.get("output"), str):
                yield item, "output", str(item.get("call_id") or f"responses_{index}")


def _head_tail_preview(content: str, max_chars: int) -> str:
    head_chars = max(1, int(max_chars * _HEAD_FRACTION))
    tail_chars = max(1, max_chars - head_chars)
    return (
        content[:head_chars]
        + "\n... [middle omitted from request; full output is on disk] ...\n"
        + content[-tail_chars:]
    )


def _spill_for_request(content: str, tool_use_id: str, max_inline_chars: int) -> str | None:
    digest = hashlib.sha256(
        f"request:{tool_use_id}:{len(content)}".encode("utf-8", errors="replace")
    ).hexdigest()[:20]
    path = _write_to_spillover(content, f"request_{digest}.txt")
    if path is None:
        return None
    preview = _head_tail_preview(content, max_inline_chars)
    return _build_persisted_message(preview, True, len(content), path)


def guard_request_body_size(
    payload: dict[str, Any],
    *,
    max_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
    max_inline_tool_chars: int = DEFAULT_MAX_INLINE_TOOL_CHARS,
) -> tuple[dict[str, Any], RequestSizeReport]:
    """Bound final request kwargs and return a content-free size report.

    A copy is allocated only when an oversized tool result must be replaced.
    The caller's conversation history is never mutated, preserving its prompt
    cache prefix and durable transcript. Repeated retries are idempotent because
    persisted-output stubs are already below the inline threshold and tagged.
    """
    before = _serialized_body_bytes(payload)
    oversized = [
        (container, field, tool_id)
        for container, field, tool_id in _tool_output_slots(payload)
        if len(container[field]) > max_inline_tool_chars
        and PERSISTED_OUTPUT_TAG not in container[field]
    ]
    if before <= max_body_bytes and not oversized:
        return payload, RequestSizeReport(before, before, 0, "within_budget")

    guarded = copy.deepcopy(payload) if oversized else payload
    compacted = 0
    if oversized:
        # Re-discover slots on the copy; container identities from payload do
        # not map across deepcopy.
        for container, field, tool_id in _tool_output_slots(guarded):
            content = container[field]
            if len(content) <= max_inline_tool_chars or PERSISTED_OUTPUT_TAG in content:
                continue
            replacement = _spill_for_request(content, tool_id, max_inline_tool_chars)
            if replacement is not None:
                container[field] = replacement
                compacted += 1

    after = _serialized_body_bytes(guarded)
    reason = "oversized_tool_results" if compacted else "body_budget_exceeded"
    logger.info(
        "request body preflight: before_bytes=%d after_bytes=%d "
        "compacted_tool_results=%d reason=%s",
        before,
        after,
        compacted,
        reason,
    )
    if after > max_body_bytes:
        raise RequestBodyTooLarge(
            "Request body remains oversized after safe tool-result compaction; "
            f"before_bytes={before} after_bytes={after} "
            f"max_body_bytes={max_body_bytes} reason={reason}. "
            "No network request was opened. Start a new session or compact "
            "the conversation before retrying."
        )
    return guarded, RequestSizeReport(before, after, compacted, reason)
