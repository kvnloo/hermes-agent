"""User pins: text the user marks with ``/pin`` so every compaction summary carries it verbatim.

A pin is one ``kind='pin'`` row of the decision ledger (no second store). Pins are user-only: every write here
takes the writer's ``origin`` and refuses anything but ``"user"``, and the ledger's generic append refuses the
``pin`` kind, so approvals, steers, tools, plugins and the model cannot create one. There is a fixed cap; an add
past it is refused with a plain error and nothing is evicted, by recency or by the summarizer.

At compaction the pins are rendered from the ledger into a ``## Pinned by the user`` block of the summary,
replacing any copy the summarizer wrote, so they are carried mechanically and never re-summarized. A
deterministic check then compares each pin with the new summary's own prose and flags a sentence that looks
like it contradicts the pin (see :func:`find_contradictions` for what it can and cannot catch).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from agent.decision_ledger import MAX_LEDGER_TEXT_BYTES, ledger_repository

logger = logging.getLogger(__name__)

MAX_PINS = 8
MAX_PIN_BYTES = MAX_LEDGER_TEXT_BYTES
PINNED_HEADING = "## Pinned by the user"
_PINNED_NOTE = ("(Pinned by the user with /pin and copied here verbatim from the session's decision ledger at every "
                "compaction. These are the user's exact words; they override any paraphrase above.)")
_CONTRADICTION_PREFIX = "Possible contradiction with pin"
USER_ORIGIN = "user"


class PinRefused(ValueError):
    """A pin write that was not made: the message is the plain reason shown to the user."""


def _require_user(origin: str) -> None:
    if origin != USER_ORIGIN:
        raise PinRefused(f"Pins are user-only; a write from {origin or 'an unknown source'!r} was refused.")


def _verbatim_text(text: Any) -> str:
    """The pin text as given, or a refusal: a pin is stored and replayed byte for byte, so text the ledger would
    have to cut or redact is refused rather than altered."""
    if not isinstance(text, str) or not text.strip():
        raise PinRefused("Nothing to pin.")
    if len(text.encode("utf-8")) > MAX_PIN_BYTES:
        raise PinRefused(f"That pin is longer than {MAX_PIN_BYTES} bytes; pin a shorter excerpt.")
    from agent.decision_ledger import bounded_decision_text
    if bounded_decision_text("pin", text) != text:
        raise PinRefused("That text looks like it contains a credential, so it was not pinned.")
    return text


def list_pins(repository, session_id: str) -> list[str]:
    reader = getattr(repository, "get_decision_ledger_entries", None)
    if not session_id or not callable(reader):
        return []
    return [entry["text"] for entry in reader(session_id) if entry.get("kind") == "pin"]


def add_pin(repository, session_id: str, text: Any, *, origin: str) -> int:
    """Pin ``text``; returns the new pin's number (1-based). Raises :class:`PinRefused`."""
    _require_user(origin)
    text = _verbatim_text(text)
    if not session_id or not callable(getattr(repository, "add_pin", None)):
        raise PinRefused("No session store is available, so nothing was pinned.")
    position = repository.add_pin(session_id, text, limit=MAX_PINS)
    if position is None:
        raise PinRefused(f"You already have {MAX_PINS} pins, the maximum. Remove one with /unpin <n> first; "
                         "nothing was pinned and no pin was removed.")
    return position


def remove_pin(repository, session_id: str, number: int, *, origin: str) -> str:
    """Remove pin ``number`` (1-based); returns its text. Raises :class:`PinRefused`."""
    _require_user(origin)
    removed = repository.remove_pin(session_id, number) if session_id else None
    if removed is None:
        raise PinRefused(f"There is no pin {number}. /pins lists them.")
    return removed


def patch_pin(repository, session_id: str, number: int, text: Any, *, origin: str) -> None:
    """Replace pin ``number``'s text, keeping its place. Raises :class:`PinRefused`."""
    _require_user(origin)
    text = _verbatim_text(text)
    if not session_id or not repository.patch_pin(session_id, number, text):
        raise PinRefused(f"There is no pin {number}. /pins lists them.")


# -- compaction --------------------------------------------------------------------------------------------------

def render_pins_block(pins: list[str], flags: Optional[list[dict]] = None) -> str:
    lines = [PINNED_HEADING, *(f"{index}. {text}" for index, text in enumerate(pins, 1)), _PINNED_NOTE]
    for flag in flags or ():
        lines.append(f"{_CONTRADICTION_PREFIX} {flag['pin_number']}: the summary above says "
                     f"\"{flag['sentence']}\" ({flag['reason']}). The pin is the user's instruction.")
    return "\n".join(lines)


def _strip_pins_block(text: str) -> str:
    """Remove any ``## Pinned by the user`` section (ours or a summarizer's copy) up to the next heading."""
    start = text.find(PINNED_HEADING)
    while start >= 0:
        end = text.find("\n## ", start + len(PINNED_HEADING))
        tail = "" if end < 0 else text[end:]
        if end < 0:
            from session_rules.turns import _SUMMARY_END_MARKER
            marker = text.find(_SUMMARY_END_MARKER, start)
            tail = "" if marker < 0 else "\n\n" + text[marker:]
        text = text[:start].rstrip() + tail
        start = text.find(PINNED_HEADING)
    return text


def _summary_index(compressed: list) -> Optional[int]:
    from agent.context_compressor import is_compaction_summary_message
    for index, message in enumerate(compressed):
        if isinstance(message, dict) and isinstance(message.get("content"), str) and is_compaction_summary_message(message):
            return index
    return None


def _narrative(summary: str) -> str:
    """The summarizer's own prose: without the pinned block and the verbatim user quotes (the user's words)."""
    from agent.context_compressor import _LEAN_USER_MESSAGES_HEADING
    text = _strip_pins_block(summary)
    start = text.find(_LEAN_USER_MESSAGES_HEADING)
    if start >= 0:
        end = text.find("\n## ", start + 1)
        text = text[:start] + ("" if end < 0 else text[end:])
    return text


def fold_pins_into_summary(agent: Any, compressed: list) -> list[dict]:
    """Render the session's pins into the compaction summary; returns the contradiction flags raised."""
    session_id = getattr(agent, "session_id", "") or ""
    try:
        pins = list_pins(ledger_repository(agent), session_id)
    except Exception:
        logger.debug("Could not load pins for compaction", exc_info=True)
        return []
    if not pins:
        return []
    index = _summary_index(compressed)
    if index is None:
        # No summary message (a context engine that writes none): carry the pins in the ledger carrier.
        from agent.conversation_compression_ledger import append_to_ledger_carrier
        append_to_ledger_carrier(compressed, render_pins_block(pins))
        return []
    message = compressed[index]
    summary = _strip_pins_block(message["content"])
    flags = find_contradictions(pins, _narrative(summary))
    block = "\n\n" + render_pins_block(pins, flags)
    from session_rules.turns import _SUMMARY_END_MARKER
    marker = summary.rfind(_SUMMARY_END_MARKER)
    summary = summary.rstrip() + block if marker < 0 else summary[:marker].rstrip() + block + "\n\n" + summary[marker:]
    from agent.conversation_compression import _replace_message_content
    _replace_message_content(message, summary)
    agent._pin_contradictions = flags
    for flag in flags:
        logger.warning("Compaction summary may contradict pin %d (%s): %r", flag["pin_number"], flag["reason"],
                       flag["sentence"])
    return flags


# -- contradiction check -----------------------------------------------------------------------------------------
# A conservative, deterministic heuristic, no model call. It reads each pin's content words and polarity, then
# looks for a summary sentence that (a) uses an antonym of one of those words, or (b) shares at least two of them
# (one for a one-word pin) with the opposite negation polarity. It catches direct flips ("keep this offline" ->
# "publish it online", "never push to main" -> "push to main"). It misses paraphrases that share no words and no
# listed antonym, sarcasm, double negatives and scope changes ("only on Fridays"), and can flag an unrelated
# sentence that happens to reuse the pin's words with a negation. It is a flag for the reader, never an edit.

_NEGATIONS = frozenset({"not", "no", "never", "don't", "dont", "doesn't", "doesnt", "didn't", "didnt", "won't",
                        "wont", "can't", "cant", "cannot", "shouldn't", "shouldnt", "mustn't", "mustnt", "isn't",
                        "isnt", "aren't", "arent", "without", "avoid", "stop", "nor", "none", "neither"})
_STOPWORDS = frozenset({"a", "an", "the", "this", "that", "these", "those", "it", "its", "is", "are", "was", "were",
                        "be", "been", "to", "of", "in", "on", "for", "and", "or", "with", "as", "at", "by", "from",
                        "we", "you", "i", "me", "my", "our", "your", "they", "them", "he", "she", "please", "should",
                        "must", "will", "would", "can", "could", "do", "does", "did", "all", "any", "so", "then",
                        "user", "asked", "wants", "want", "said", "says", "keep", "make", "use", "always"})
_ANTONYM_PAIRS = (
    ("offline", "online"), ("private", "public"), ("local", "remote"), ("local", "cloud"), ("enable", "disable"),
    ("enabled", "disabled"), ("allow", "deny"), ("allow", "forbid"), ("allowed", "forbidden"), ("include", "exclude"),
    ("keep", "delete"), ("keep", "remove"), ("always", "never"), ("internal", "external"), ("manual", "automatic"),
    ("sync", "async"), ("before", "after"), ("encrypted", "unencrypted"), ("secret", "public"), ("draft", "publish"),
    ("draft", "published"), ("staging", "production"), ("read-only", "write"), ("approve", "reject"),
)
_ANTONYMS: dict[str, set[str]] = {}
for _a, _b in _ANTONYM_PAIRS:
    _ANTONYMS.setdefault(_a, set()).add(_b)
    _ANTONYMS.setdefault(_b, set()).add(_a)
_WORD = re.compile(r"[a-z0-9][a-z0-9'_-]*")
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("\u2019", "'"))


def _negated(words: list[str]) -> bool:
    return sum(1 for w in words if w in _NEGATIONS or w.endswith("n't")) % 2 == 1


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def find_contradictions(pins: list[str], summary: str) -> list[dict]:
    flags = []
    sentences = [s.strip() for s in _SENTENCE.findall(summary) if s.strip()]
    for number, pin in enumerate(pins, 1):
        pin_words = _words(pin)
        raw_terms = {w for w in pin_words if w not in _NEGATIONS and not w.endswith("n't")}
        terms = {_stem(w) for w in raw_terms if w not in _STOPWORDS}
        antonyms = {a for w in raw_terms for a in _ANTONYMS.get(w, ())}
        pin_negated = _negated(pin_words)
        for sentence in sentences:
            words = _words(sentence)
            stems = {_stem(w) for w in words}
            flipped = sorted(antonyms & set(words))
            if flipped:
                flags.append({"pin_number": number, "pin": pin, "sentence": sentence,
                              "reason": f"uses {flipped[0]!r}, the opposite of a pinned word"})
                break
            shared = terms & stems
            if terms and len(shared) >= min(2, len(terms)) and _negated(words) != pin_negated:
                flags.append({"pin_number": number, "pin": pin, "sentence": sentence,
                              "reason": "same words with the opposite negation"})
                break
    return flags
