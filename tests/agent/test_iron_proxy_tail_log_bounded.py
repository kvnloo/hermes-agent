"""Bounded-I/O regression tests for ``_tail_log`` in ``agent/proxy_sources/iron_proxy.py``.

``iron-proxy.log`` is opened append-only and never rotated, so it accumulates
across gateway restarts. ``_tail_log`` only ever consumes the last ~8KB /
last 20 lines, so it must not read the whole file.
"""

import builtins
from pathlib import Path

import pytest

from agent.proxy_sources.iron_proxy import _tail_log

_WINDOW = 8192
# Headroom for bookkeeping; the tail read itself must stay within the window.
_SLACK = 1024


class _ByteCounter:
    """Counts every byte handed out via ``open()`` and ``Path.read_bytes()``."""

    def __init__(self, monkeypatch):
        self.via_open = 0
        self.via_read_bytes = 0
        counter = self
        real_open = builtins.open
        real_read_bytes = Path.read_bytes

        class _CountingFile:
            def __init__(self, f):
                self._f = f

            def read(self, n=-1):
                data = self._f.read(n)
                counter.via_open += len(data)
                return data

            def readline(self, *args):
                data = self._f.readline(*args)
                counter.via_open += len(data)
                return data

            def readlines(self, *args):
                data = self._f.readlines(*args)
                counter.via_open += sum(len(chunk) for chunk in data)
                return data

            def __enter__(self):
                self._f.__enter__()
                return self

            def __exit__(self, *exc):
                return self._f.__exit__(*exc)

            def __getattr__(self, name):
                return getattr(self._f, name)

        def _open(*args, **kwargs):
            return _CountingFile(real_open(*args, **kwargs))

        def _read_bytes(path_self):
            data = real_read_bytes(path_self)
            counter.via_read_bytes += len(data)
            return data

        monkeypatch.setattr(builtins, "open", _open)
        monkeypatch.setattr(Path, "read_bytes", _read_bytes)

    @property
    def total(self):
        return self.via_open + self.via_read_bytes


def _big_log(path: Path, size: int = 2 * 1024 * 1024) -> bytes:
    lines, data = [], b""
    i = 0
    while len(data) < size:
        line = f"2026-09-25 line {i:08d} some proxy log content padding xxxxxxxxxx\n".encode()
        lines.append(line)
        data += line
        i += 1
    path.write_bytes(data)
    return data


def test_tail_log_reads_at_most_window_bytes(tmp_path, monkeypatch):
    log = tmp_path / "iron-proxy.log"
    data = _big_log(log)
    counter = _ByteCounter(monkeypatch)

    out = _tail_log(log)

    assert counter.total <= _WINDOW + _SLACK, (
        f"_tail_log read {counter.total} bytes from a {len(data)}-byte log; "
        f"only the last {_WINDOW} bytes are ever consumed"
    )
    expected = "\n".join(data[-_WINDOW:].decode("utf-8", errors="replace").splitlines()[-20:])
    assert out == expected


def test_tail_log_small_file_reads_whole_file(tmp_path, monkeypatch):
    log = tmp_path / "iron-proxy.log"
    log.write_text("alpha\nbeta\ngamma\n")
    counter = _ByteCounter(monkeypatch)

    assert _tail_log(log) == "alpha\nbeta\ngamma"
    assert counter.total <= _WINDOW + _SLACK


def test_tail_log_missing_file(tmp_path):
    assert _tail_log(tmp_path / "iron-proxy.log") == "(no log file)"
