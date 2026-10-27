"""Pure policy for poisoned Hermes kanban worker sessions (#664).

No session state, environment, delay, persistence or network access is touched.
The caller retains exclusive responsibility for proving its live kanban claim
before any model entry, including entry into a replacement session.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from agent.error_classifier import FailoverReason
from agent.kanban_turn_recovery import _NON_RECOVERABLE_REASONS


RecoveryAction = Literal["in_place", "fresh_session", "stop"]


@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    reason: str
    signature: str | None


# Reuse the existing recovery gate's three quota/billing reasons. That module
# currently exposes no public alias; the eventual wiring can promote one.
_STOP_REASONS = _NON_RECOVERABLE_REASONS | frozenset({
    FailoverReason.auth_permanent.value,
    FailoverReason.model_entitlement.value,
    FailoverReason.content_policy_blocked.value,
    FailoverReason.data_policy_denied.value,
})

_SESSION_BORNE_REASONS = frozenset({
    FailoverReason.context_overflow.value,
    FailoverReason.payload_too_large.value,
    FailoverReason.format_error.value,
    FailoverReason.role_alternation.value,
    FailoverReason.invalid_encrypted_content.value,
    FailoverReason.thinking_signature.value,
    FailoverReason.image_corrupt.value,
})

_TERMINAL_EXIT_PREFIX = "max_iterations_reached"
_ERROR_CLASS_FIELDS = ("error_class", "failure_error_class", "exception_type", "error_type")
_EXCEPTION_NAME = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Timeout|Failure))\b", re.IGNORECASE
)
_URL = re.compile(r"\b(?:https?|file)://[^\s,;)\]}>\"']+", re.IGNORECASE)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_PATH = re.compile(r"(?<!\w)(?:[A-Za-z]:[\\/]|\\\\|/)[^\s,;)\]}>\"']+")
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_NAMED_ID = re.compile(
    r"\b(?:request|req|trace|span|session|run|task|tool(?:[_-]call)?|call|correlation)"
    r"[_ -]?id\s*(?:[:=#]\s*|\s+)[\w.-]+",
    re.IGNORECASE,
)
_LONG_HEX_ID = re.compile(r"\b(?:0x)?[a-f0-9]{12,}\b", re.IGNORECASE)
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DIGITS = re.compile(r"\d+")
_SPACE = re.compile(r"\s+")


def _terminal(result: Mapping[str, Any]) -> bool:
    """A completed, interrupted or already-settled turn cannot be restarted."""
    return (
        result.get("completed") is True
        or result.get("interrupted") is True
        or str(result.get("turn_exit_reason") or "").startswith(_TERMINAL_EXIT_PREFIX)
    )


def _failure_reason(result: Mapping[str, Any]) -> str:
    reason = result.get("failure_reason")
    if isinstance(reason, FailoverReason):
        return reason.value
    return str(reason or FailoverReason.unknown.value)


def _first_error_line(result: Mapping[str, Any]) -> str:
    value = result.get("error") or result.get("final_response") or ""
    if not isinstance(value, str):
        return ""
    lines = value.strip().splitlines()
    return lines[0] if lines else ""


def _normalize_line(value: str, *, limit: int) -> str:
    """Keep failure *kind*, never variable ids, addresses, paths or numbers."""
    value = _URL.sub("<url>", value)
    value = _EMAIL.sub("<email>", value)
    value = _PATH.sub("<path>", value)
    value = _UUID.sub("<id>", value)
    value = _NAMED_ID.sub("<id>", value)
    value = _LONG_HEX_ID.sub("<id>", value)
    value = _IP.sub("<ip>", value)
    value = _DIGITS.sub("#", value)
    value = _SPACE.sub(" ", value).strip(" \t.:;,").casefold()
    return value[:limit] or "unspecified"


def _error_class(result: Mapping[str, Any], first_line: str) -> str:
    for key in _ERROR_CLASS_FIELDS:
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_line(value.rsplit(".", 1)[-1], limit=48)
    match = _EXCEPTION_NAME.search(first_line)
    return _normalize_line(match.group(1).rsplit(".", 1)[-1], limit=48) if match else "unclassified"


def failure_signature(result: Mapping[str, Any]) -> str | None:
    """Short stable signature of a failed, nonterminal settled turn.

    The message portion is only the first error line, scrubbed of run-specific
    paths, identifiers and numeric values. Conversation messages are ignored.
    """
    if result.get("failed") is not True or _terminal(result):
        return None
    first_line = _first_error_line(result)
    reason = _normalize_line(_failure_reason(result), limit=48)
    error_class = _error_class(result, first_line)
    message = _normalize_line(first_line, limit=128)
    return f"{reason}|{error_class}|{message}"


def classify_failure(
    results: Sequence[Mapping[str, Any]], *, repetition_threshold: int = 2,
) -> RecoveryDecision:
    """Choose recovery for the latest settled turn without initiating a retry.

    Fail-closed stop rules win over session replacement, which wins over
    consecutive-signature detection. A success breaks a repetition streak.
    The optional threshold is a config.yaml-driven policy value, not an env var.
    """
    if isinstance(repetition_threshold, bool) or repetition_threshold < 2:
        raise ValueError("repetition_threshold must be an integer >= 2")
    if not results:
        return RecoveryDecision("stop", "no_settled_failure", None)

    latest = results[-1]
    if latest.get("failed") is not True:
        return RecoveryDecision("stop", "not_a_failed_turn", None)
    if _terminal(latest):
        return RecoveryDecision("stop", "terminal_turn", None)

    reason = _failure_reason(latest)
    signature = failure_signature(latest)
    if reason in _STOP_REASONS:
        return RecoveryDecision("stop", "non_recoverable_reason", signature)
    if reason in _SESSION_BORNE_REASONS:
        return RecoveryDecision("fresh_session", "session_borne_failure", signature)

    if signature and len(results) >= repetition_threshold:
        tail = results[-repetition_threshold:]
        if all(failure_signature(item) == signature for item in tail):
            return RecoveryDecision("fresh_session", "repeated_failure", signature)

    return RecoveryDecision("in_place", "transient_failure", signature)


_FRESH_TERMINAL_INSTRUCTION = (
    "\n\nStart in a NEW session; never replay previous conversation history. "
    "Finish with a real terminal kanban_complete(...) or kanban_block(...) tool call."
)
_SIGNATURE_HEADER = "\n\nPrior failure signatures (not conversation history):"


def fresh_session_seed(
    task_body: str, prior: Sequence[Mapping[str, Any]], *, max_chars: int = 4000,
) -> str:
    """Bounded first *user* message for a replacement session, never a replay.

    Include the original task, deduplicated diagnostic signatures, and a real
    terminal kanban instruction. In a tiny budget, the terminal instruction
    takes precedence over diagnostics; no previous message/tool text is copied.
    """
    if max_chars < 0:
        raise ValueError("max_chars must be nonnegative")
    if max_chars <= len(_FRESH_TERMINAL_INSTRUCTION):
        return _FRESH_TERMINAL_INSTRUCTION[:max_chars]

    available = max_chars - len(_FRESH_TERMINAL_INSTRUCTION)
    distinct = tuple(dict.fromkeys(
        sig for result in prior if (sig := failure_signature(result)) is not None
    ))[-12:]
    signature_budget = min(1100, available // 3)
    lines = ""
    for signature in distinct:
        new_line = f"\n- {signature}"
        if len(_SIGNATURE_HEADER) + len(lines) + len(new_line) > signature_budget:
            break
        lines += new_line
    diagnostics = (_SIGNATURE_HEADER + lines) if lines else ""
    task = ("Task:\n" + task_body.strip())[:available - len(diagnostics)]
    return task + diagnostics + _FRESH_TERMINAL_INSTRUCTION


__all__ = [
    "RecoveryDecision",
    "classify_failure",
    "failure_signature",
    "fresh_session_seed",
]
