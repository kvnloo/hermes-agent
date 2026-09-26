"""Private run-document diagnostics, kept separate from delivery summaries."""

from pathlib import Path
from traceback import format_exception

from agent.redact import redact_sensitive_text

# Enough for a Python traceback's last frames plus the exception line.
_WORKER_STDERR_TAIL_CHARS = 1500
# Byte window for the bounded tail read: worst-case 4 bytes/char (UTF-8) plus margin
# for trailing whitespace the strip() below removes and for a split multibyte
# sequence at the window edge (decoded with errors="replace").
_TAIL_READ_WINDOW_BYTES = _WORKER_STDERR_TAIL_CHARS * 4 + 4096


def _read_tail_text(path: Path, tail_chars: int) -> tuple[str, bool]:
    """Last ``tail_chars`` chars of a text file's stripped content, without reading it whole.

    The stderr capture is unbounded in principle (a dying worker can spew), but the only
    consumer keeps the last 1500 chars, so a full ``read_text()`` scales with junk bytes.
    Seeks to the last window of the file and decodes from there; files within the window
    read whole, exactly like before. Returns ``(tail, truncated)``, where ``truncated``
    says the stripped file exceeded ``tail_chars`` — the old ellipsis rule.

    Approximation: past the window the tail is exact only when the last ``tail_chars``
    chars plus trailing whitespace fit the window (4 bytes/char worst case plus a 4KB
    margin); a multi-KB trailing-whitespace run is the only divergence, and the old code
    paid a full read of every file to cover it.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return "", False
    try:
        with open(path, "rb") as fh:
            if size > _TAIL_READ_WINDOW_BYTES:
                fh.seek(size - _TAIL_READ_WINDOW_BYTES)
            raw = fh.read()
    except OSError:
        return "", False
    text = raw.decode("utf-8", errors="replace").strip()
    if size <= _TAIL_READ_WINDOW_BYTES:
        return text[-tail_chars:], len(text) > tail_chars
    # Past the window the stripped file is longer than tail_chars in every realistic
    # case (the exception is a >10KB file of pure leading whitespace — invisible).
    return text[-tail_chars:], len(text) >= tail_chars


def format_run_error(exc: BaseException) -> str:
    """Retain chained causes without capturing locals or exposing URL credentials."""
    traceback_text = redact_sensitive_text(
        "".join(format_exception(exc)), force=True, redact_url_credentials=True,
    )
    return f"## Error\n\n```\n{traceback_text}\n```\n"


def external_worker_stderr_tail(path: Path) -> str:
    """Redacted tail of a restart-safe cron worker's captured stderr, as a message suffix.

    The gateway used to spawn the worker with ``stderr=DEVNULL``, so a worker that died before
    publishing its acknowledgement (an import error, a missing module in the interpreter it was
    handed) only ever reported ``exit 1`` and the reporter had to guess the cause (#112729).
    Returns an empty string when nothing was captured.
    """
    text, truncated = _read_tail_text(path, _WORKER_STDERR_TAIL_CHARS)
    if not text:
        return ""
    if truncated:
        text = "…" + text
    tail = redact_sensitive_text(text, force=True, redact_url_credentials=True)
    return f"; worker stderr: {tail}"
