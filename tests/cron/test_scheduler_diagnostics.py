"""Worker stderr tail: bounded read, same observable contract as the full read.

Sibling of the update-output tail-read fix: ``external_worker_stderr_tail`` kept only
the last 1500 chars of a worker's captured stderr but read the whole file to get them.
"""
import io

import pytest

from agent.redact import redact_sensitive_text
from cron import scheduler_diagnostics as sd

# Must stay in sync with the implementation's window: 1500 chars worst-case
# 4 bytes/char (UTF-8) plus margin. A literal here (not sd._ATTR) keeps the
# bounded test red on base, where the attribute does not exist.
_MAX_READ_BYTES = 1500 * 4 + 4096


def _oracle_tail(content: str) -> str:
    """The documented contract: stripped tail, ellipsis when cut, then redacted."""
    stripped = content.strip()
    if not stripped:
        return ""
    tail = stripped[-sd._WORKER_STDERR_TAIL_CHARS:]
    if len(stripped) > sd._WORKER_STDERR_TAIL_CHARS:
        tail = "…" + tail
    return "; worker stderr: " + redact_sensitive_text(
        tail, force=True, redact_url_credentials=True)


TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "<stdin>", line 1, in <module>\n'
    "ModuleNotFoundError: No module named 'hermes_worker'\n"
)


@pytest.mark.parametrize("content", [
    TRACEBACK,
    "x" * sd._WORKER_STDERR_TAIL_CHARS,          # exactly the tail: no ellipsis
    "y" * (sd._WORKER_STDERR_TAIL_CHARS + 1),    # one over: ellipsis
    "z" * 20_000 + "final-marker",               # large file, real tail past the window
    "é" * 10_000 + "tail-héllo",                 # multibyte across the window edge
    "   \n\t  ",                                # whitespace-only
])
def test_worker_stderr_tail_matches_full_read_contract(tmp_path, content):
    target = tmp_path / "worker.stderr"
    target.write_text(content, encoding="utf-8")
    assert sd.external_worker_stderr_tail(target) == _oracle_tail(content)


def test_worker_stderr_tail_missing_file_is_empty(tmp_path):
    assert sd.external_worker_stderr_tail(tmp_path / "nope.stderr") == ""


def test_worker_stderr_tail_read_is_bounded(tmp_path, monkeypatch):
    """The red-on-base proof: a 2MB stderr capture must not cost a 2MB read."""
    target = tmp_path / "worker.stderr"
    target.write_bytes(b"spam-line\n" * 200_000 + b"final-boom\n")

    real_open = open
    total_read = 0

    class _SpyReader:
        def __init__(self, fh):
            self._fh = fh

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return self._fh.__exit__(*exc)

        def seek(self, *args):
            return self._fh.seek(*args)

        def read(self, *args):
            data = self._fh.read(*args)
            nonlocal total_read
            total_read += len(data)
            return data

    def _spy_open(*args, **kwargs):
        return _SpyReader(real_open(*args, **kwargs))

    # builtins.open covers the new bounded read; io.open covers Path.read_text on base.
    monkeypatch.setattr("builtins.open", _spy_open)
    monkeypatch.setattr(io, "open", _spy_open)

    out = sd.external_worker_stderr_tail(target)
    assert out.endswith("final-boom")
    assert total_read <= _MAX_READ_BYTES
