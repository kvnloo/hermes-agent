"""Bounded decision events; text is evidence, never an executable approval gate.

The store keeps what it is given (the storage layer's convention: the caller redacts), so every write goes
through :func:`record_decision`, which bounds and redacts the text first. ``ledger_repository`` picks the
agent's storage-interface ``sessions`` repository, or a legacy store object that carries the same verbs."""

import logging

logger = logging.getLogger(__name__)

MAX_LEDGER_ENTRIES = 50
MAX_LEDGER_TEXT_BYTES = 2048
MAX_LEDGER_TURN_BYTES = 128
LEDGER_PRIORITY = {"denial": 0, "correction": 1, "approval": 2, "preference": 3}


def omitted_decision(kind: str, reason: str) -> str:
    return f"[Text omitted: {reason}; {kind} remains recorded. Do not infer permission; ask the user to restate scope.]"


def bounded_decision_text(kind: str, text: str, *, limit: int = MAX_LEDGER_TEXT_BYTES) -> str:
    # Reject the WHOLE text rather than cut away a trailing negation or scope.
    # Check before redaction to bound the redactor's work on arbitrary input.
    if len(text) > limit or len(text.encode("utf-8")) > limit:
        return omitted_decision(kind, "size limit")
    from agent.redact import redact_for_egress, redact_sensitive_text
    try:
        text = redact_sensitive_text(text, force=True, redact_url_credentials=True)
        text = redact_for_egress(text)
    except Exception:
        logger.debug("Decision ledger redaction unavailable", exc_info=True)
        return omitted_decision(kind, "redaction unavailable")
    if len(text.encode("utf-8")) > limit:
        return omitted_decision(kind, "size limit after redaction")
    return text


def bounded_ledger_turn_id(turn_id: str) -> str:
    text = bounded_decision_text("decision", turn_id or "", limit=MAX_LEDGER_TURN_BYTES)
    return text if len(text.encode("utf-8")) <= MAX_LEDGER_TURN_BYTES else "[turn id omitted]"


def ledger_repository(agent):
    """The object carrying the decision-ledger verbs for ``agent``: the storage interface's ``sessions``
    repository when the agent writes through one, else its ``_session_db`` (a worker store or a test double)."""
    from agent.agent_init_session import agent_interface
    store = agent_interface(agent)
    if store is not None:
        return store.sessions
    return getattr(agent, "_session_db", None)


def record_decision(repository, session_id: str, kind: str, text: str, *, turn_id: str = "") -> bool:
    """Bound, redact and append one decision; False when there is nothing to write or no ledger verb."""
    if kind not in LEDGER_PRIORITY:
        raise ValueError(f"Unsupported decision ledger kind: {kind!r}")
    recorder = getattr(repository, "append_decision_ledger_entry", None)
    if not session_id or not callable(recorder) or not isinstance(text, str) or not text:
        return False
    recorder(session_id, kind, bounded_decision_text(kind, text), turn_id=bounded_ledger_turn_id(turn_id))
    return True
