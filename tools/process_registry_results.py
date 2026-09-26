"""Bounded, profile-local receipts for completed terminal processes.

Receipts are read through process_manage, never replayed as notifications or
adopted as live PIDs. Each producer writes its own file so independent one-shot
parents cannot overwrite each other's results in the running-PID checkpoint.
"""

import json
import logging
import re
import sqlite3
import time

from hermes_constants import get_hermes_home
from utils import atomic_json_write

logger = logging.getLogger("tools.process_registry")

RESULT_RETENTION_SECONDS = 7 * 24 * 60 * 60
MAX_RETAINED_RESULTS = 64
_RESULT_FIELDS = (
    "id", "command", "cwd", "task_id", "owner_task_id", "session_key",
    "parent_session_id", "started_at", "exit_code", "completion_reason",
    "termination_source", "notify_on_complete",
)


def _result_paths():
    """Prune by completion time, not start time (jobs can take days)."""
    directory = get_hermes_home() / "logs" / "process-results"
    cutoff = time.time() - RESULT_RETENTION_SECONDS
    retained = []
    for path in directory.glob("proc_*.json"):
        try:
            modified = path.stat().st_mtime
            if modified < cutoff:
                path.unlink(missing_ok=True)
            else:
                retained.append((modified, path))
        except FileNotFoundError:
            continue  # Another producer pruned it.
    retained.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    for _, path in retained[MAX_RETAINED_RESULTS:]:
        path.unlink(missing_ok=True)
    return [path for _, path in retained[:MAX_RETAINED_RESULTS]]


def save_completed_result(session) -> None:
    from agent.redact import redact_sensitive_text, redact_terminal_output
    from tools.process_registry import MAX_OUTPUT_CHARS

    with session._lock:
        record = {key: getattr(session, key) for key in _RESULT_FIELDS}
        record["output"] = session.output_buffer[-MAX_OUTPUT_CHARS:]
    # Live-output opt-out must not persist raw credentials in durable receipts.
    record["output"] = redact_terminal_output(record["output"], record["command"], force=True)
    record["command"] = redact_sensitive_text(record["command"], code_file=True, force=True)
    directory = get_hermes_home() / "logs" / "process-results"
    try:
        from hermes_constants import assert_named_profile_home_live
        assert_named_profile_home_live(directory)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        atomic_json_write(directory / f"{session.id}.json", record, mode=0o600)
        _result_paths()
    except OSError:
        # Preserve live delivery on disk failure, but never silently claim durability.
        logger.warning("Could not retain completed process result %s", session.id, exc_info=True)


def _owns_result(owner: str, parent: str | None) -> bool:
    if not parent:
        return False
    if owner == parent:
        return True
    from hermes_state import SessionDB

    # Pure lineage read on the hot path of every retained-result load; a writable open here
    # was one more writer handle per call inside the gateway (#100896).
    db = SessionDB(read_only=True)
    try:
        return db.get_compression_tip(parent) == owner
    finally:
        db.close()


def _introduces_escape(raw: str, i: int) -> bool:
    """Whether the backslash at ``raw[i]`` starts an escape (even run before it)."""
    run = 0
    j = i - 1
    while j >= 0 and raw[j] == "\\":
        run += 1
        j -= 1
    return run % 2 == 0


def _prev_token_start(raw: str, p: int) -> int:
    """Start index of the JSON string token ending at boundary ``p``.

    Tokens are one plain char, a 2-char ``\\X`` escape, or a 6-char
    ``\\uXXXX`` escape. A backslash at ``p - 1`` always closes a ``\\\\``
    pair here: at a true boundary its run is even (an odd run would leave one
    backslash starting an escape past ``p`` — impossible). A low surrogate
    preceded by a high surrogate is one decoded char (surrogate pair): step
    over both, never cut between them.
    """
    if raw[p - 1] == "\\":
        return p - 2  # trailing \\ pair is one token
    if p >= 2 and raw[p - 2] == "\\" and _introduces_escape(raw, p - 2):
        return p - 2  # \X escape
    if (
        p >= 6
        and raw[p - 6] == "\\"
        and raw[p - 5] == "u"
        and all(c in "0123456789abcdefABCDEF" for c in raw[p - 4:p])
        and _introduces_escape(raw, p - 6)
    ):
        if (
            0xDC00 <= int(raw[p - 4:p], 16) <= 0xDFFF
            and p >= 12
            and raw[p - 12] == "\\"
            and raw[p - 11] == "u"
            and all(c in "0123456789abcdefABCDEF" for c in raw[p - 10:p - 6])
            and _introduces_escape(raw, p - 12)
            and 0xD800 <= int(raw[p - 10:p - 6], 16) <= 0xDBFF
        ):
            return p - 12  # surrogate pair is one token
        return p - 6  # \uXXXX escape
    return p - 1  # plain char


_TAIL_BYTES_PER_CHAR = 12
"""Worst-case raw bytes per decoded char: a ``\\uD83C\\uDF89`` surrogate pair."""

_TAIL_HEAD_BYTES = 16384
"""Bounded-read head size. The writer's non-output fields always fit; a head
that doesn't contain the ``"output"`` key falls back to a full parse."""


def _tail_cut(raw: str, tail_chars: int) -> int:
    """Index into ``raw`` where a ``tail_chars`` decoded-char suffix starts.

    Walks token boundaries backward from the string end — a cut is exact only
    at a boundary, never inside an escape and never inside a surrogate pair.
    Returns the largest boundary with at least ``tail_chars * 12`` raw chars
    after it; a decoded char takes at most 12 raw chars (``\\uD83C\\uDF89``
    surrogate pair), so the suffix always covers the tail.
    """
    want = len(raw) - tail_chars * _TAIL_BYTES_PER_CHAR
    p = len(raw)  # raw ends at the closing quote: a boundary
    while p > want:
        p = _prev_token_start(raw, p)
    return p


def _parse_tail_text(text: str, tail_chars: int) -> dict:
    """Tail-parse from full receipt text (small files; see ``_load_receipt_tail``).

    Raises ``ValueError`` on anything unfamiliar so the caller falls back to a
    full parse — never a garbled tail.
    """
    # A raw `"output"` (quotes included) cannot occur inside a JSON string
    # value, so the last occurrence is the key — which our writer emits last.
    key_idx = text.rfind('"output"')
    if key_idx <= 0:
        raise ValueError("output key not found")
    value_open = text.index('"', text.index(":", key_idx + 8) + 1)
    # The last quote closes the output value when our writer's layout holds
    # ("output" last). Anything else (hand-written, reordered) leaves stray
    # quotes in the slice below, so the tail decode raises and the caller
    # falls back to a full parse — never a garbled tail.
    value_close = text.rindex('"')
    if value_close <= value_open:
        raise ValueError("bad output value bounds")
    if text[value_close + 1:].strip() != "}":
        raise ValueError("output is not the last field")
    head_src = text[:key_idx].rstrip()
    if head_src.endswith(","):
        head_src = head_src[:-1]
    record = json.loads(head_src + "}")
    raw = text[value_open + 1:value_close]
    # Cut the tail at a token boundary so the suffix decodes to a true suffix
    # of the whole value (never split a \\X / \\uXXXX escape or surrogate pair).
    if tail_chars and len(raw) > tail_chars * _TAIL_BYTES_PER_CHAR + 64:
        raw = raw[_tail_cut(raw, tail_chars):]
    tail = json.loads('"' + raw + '"')
    record["output"] = tail[-tail_chars:] if tail_chars else ""
    return record


def _load_receipt_tail(path, tail_chars: int) -> dict:
    """Read a receipt's small fields plus only the tail of its ``output`` value.

    The listing path renders just ``output[-tail_chars:]``, but a plain
    ``json.loads`` walks every byte of the (up to 200KB) output string —
    ~5ms/MB, paid on every retained listing. Receipts are flat dicts written
    by :func:`save_completed_result` with ``"output"`` last, so parse the head
    (everything before it) normally and decode only a tail window of the raw
    output, cut at a token boundary (never inside a ``\\X`` / ``\\uXXXX``
    escape or surrogate pair). A decoded char takes at most 12 raw chars (a
    ``\\uD83C\\uDF89`` surrogate pair), so a ``12 * tail_chars`` window always
    covers the tail.

    I/O is bounded: at most ``_TAIL_HEAD_BYTES`` off the front plus the tail
    window off the end — the full file is never read. Anything unfamiliar
    (reordered fields, non-string output, non-writer header, window crossing
    JSON structure) raises and the caller falls back to a full parse: never a
    garbled tail. The fast path additionally requires the exact writer header
    (``_RESULT_FIELDS`` in order), which proves the byte layout it relies on.
    """
    size = path.stat().st_size
    window = tail_chars * _TAIL_BYTES_PER_CHAR + 512 if tail_chars else 0
    if size <= max(_TAIL_HEAD_BYTES, window):
        # Small enough that a full read is cheap; also covers tail_chars == 0
        # (no tail window needed, head alone suffices).
        return _parse_tail_text(path.read_text(encoding="utf-8-sig"), tail_chars)
    with open(path, "rb") as f:
        head_bytes = f.read(_TAIL_HEAD_BYTES)
        # The head cut can split a UTF-8 char at its end; that sits inside the
        # output value, past everything parsed from the head.
        head = head_bytes.decode("utf-8-sig", errors="replace")
        key_idx = head.rfind('"output"')
        if key_idx <= 0:
            raise ValueError("output key not found")
        head.index('"', head.index(":", key_idx + 8) + 1)  # key is followed by ": "
        head_src = head[:key_idx].rstrip()
        if head_src.endswith(","):
            head_src = head_src[:-1]
        record = json.loads(head_src + "}")
        if list(record.keys()) != list(_RESULT_FIELDS):
            raise ValueError("unfamiliar receipt header")
        if not tail_chars:
            record["output"] = ""
            return record
        f.seek(size - window)
        tail_bytes = f.read()
    # The window can start inside a UTF-8 char; drop its partial bytes. Only
    # the first char can be split (the window end is the file end).
    for _ in range(2):
        try:
            tail_text = tail_bytes.decode("utf-8")
            break
        except UnicodeDecodeError as e:
            if e.start != 0:
                raise ValueError("tail not decodable")
            tail_bytes = tail_bytes[e.end:]
    else:
        raise ValueError("tail not decodable")
    if not tail_text.rstrip().endswith("}"):
        raise ValueError("tail shape unfamiliar")
    value_close = tail_text.rindex('"')
    if tail_text[value_close + 1:].strip() != "}":
        raise ValueError("output is not the last field")
    # The window must lie wholly inside the output string value: a raw '"'
    # cannot appear inside a JSON string, so an unescaped quote before the
    # closing one means the window crossed JSON structure.
    i = 0
    while True:
        j = tail_text.find('"', i, value_close)
        if j < 0:
            break
        k, bs = j - 1, 0
        while k >= 0 and tail_text[k] == "\\":
            bs += 1
            k -= 1
        if bs % 2 == 0:
            raise ValueError("window crosses JSON structure")
        i = j + 1
    raw = tail_text[:value_close]
    if len(raw) > tail_chars * _TAIL_BYTES_PER_CHAR + 64:
        raw = raw[_tail_cut(raw, tail_chars):]
    tail = json.loads('"' + raw + '"')
    record["output"] = tail[-tail_chars:]
    return record


def _load_tail_or_full(path, tail_chars: int | None) -> dict:
    """Read one receipt: tail-only fast path, with a full-parse fallback.

    The fast path assumes the writer's layout (flat dict, ``"output"`` last);
    anything unfamiliar falls back to a full parse plus truncation, so a
    hand-written or future-format receipt still loads correctly.
    """
    if tail_chars is None:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    try:
        return _load_receipt_tail(path, tail_chars)
    except (ValueError, IndexError):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        record["output"] = record["output"][-tail_chars:] if tail_chars else ""
        return record


def load_completed_results(prefix: str = "", *, tail_chars: int | None = None) -> dict:
    """Restore read-only snapshots; no process handles, watchers, or queue events.

    ``tail_chars`` truncates each receipt's ``output`` to its last N chars at
    read time, for consumers that only render a preview (``list_sessions``
    shows ``output_buffer[-200:]``). ``None`` (default) keeps full hydration
    for ``get``/``read_log``.
    """
    from tools.process_registry import ProcessSession

    from gateway.session_context import get_session_env

    owner = get_session_env("HERMES_SESSION_ID", "")
    if not owner:
        return {}
    results = {}
    try:
        paths = _result_paths()
    except OSError:
        logger.warning("Could not read retained process results", exc_info=True)
        return results
    for path in paths:
        if not path.stem.startswith(prefix):
            continue
        try:
            record = _load_tail_or_full(path, tail_chars)
            if record["id"] != path.stem or not re.fullmatch(r"proc_[\w]+", record["id"]):
                continue
            if not _owns_result(owner, record.get("parent_session_id")):
                continue
            session = ProcessSession(
                **{key: record[key] for key in _RESULT_FIELDS},
                exited=True, output_buffer=record["output"],
            )
            session._completion_event.set()
            results[session.id] = session
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            logger.debug("Skipping unreadable process result %s", path.name, exc_info=True)
    return results
