"""Bounded tail reads of the post-update notification log.

``gateway/run_notifications.py`` used to ``read_bytes()`` the whole
``.update_output.txt`` (unbounded ``hermes update`` log) while the
notification only ever keeps the last 3500 chars. These tests pin the
bounded-read contract: correct tail, bounded I/O, equivalence with the old
full-read pipeline on realistic logs.
"""

import builtins
import random

import gateway.run_notifications as rn
from tools.ansi_strip import strip_ansi


class _CountingFile:
    """Wrap a binary file, counting bytes actually read."""

    def __init__(self, real):
        self._real = real
        self.bytes_read = 0

    def read(self, *args):
        data = self._real.read(*args)
        self.bytes_read += len(data)
        return data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return self._real.__exit__(*exc)

    def __getattr__(self, name):
        return getattr(self._real, name)


def _spy_open(monkeypatch, log):
    real_open = builtins.open

    def spy_open(path, mode="r", *args, **kwargs):
        fh = real_open(path, mode, *args, **kwargs)
        if "b" in mode:
            fh = _CountingFile(fh)
            log.append(fh)
        return fh

    monkeypatch.setattr(rn, "open", spy_open, raising=False)


def test_tail_read_is_bounded(tmp_path, monkeypatch):
    log = []
    _spy_open(monkeypatch, log)
    marker = "TAIL-MARKER-12345"
    chunk = "line \x1b[32mok\x1b[0m " + "x" * 90 + "\n"
    path = tmp_path / "update_output.txt"
    path.write_bytes((chunk * 11000 + marker + "\n").encode("utf-8"))
    assert path.stat().st_size > 1_000_000

    text = rn._read_text_tail_chars(path, 3500)

    total = sum(f.bytes_read for f in log)
    assert total <= 3500 * 4 + 4096 + 512, total
    assert text.rstrip().endswith(marker)


def test_tail_read_matches_full_read(tmp_path):
    rng = random.Random(42)
    lines = []
    for i in range(20000):
        color = f"\x1b[{rng.choice(['31', '32', '33'])}m" if i % 7 == 0 else ""
        reset = "\x1b[0m" if color else ""
        uni = "✓" if i % 11 == 0 else ""
        lines.append(f"{color}step {i}: installing package-{i} {uni} ok{reset}")
    lines.append("done FINAL-MARKER")
    path = tmp_path / "update_output.txt"
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    # Pre-fix pipeline, frozen for comparison.
    old = path.read_bytes().decode("utf-8", errors="replace")
    old_out = rn._update_output_tail(strip_ansi(old).strip(), 3500)

    new = rn._read_text_tail_chars(path, 3500)
    new_out = rn._update_output_tail(strip_ansi(new).strip(), 3500)
    assert new_out == old_out


def test_tail_read_small_and_missing(tmp_path):
    small = tmp_path / "small.txt"
    small.write_text("hello", encoding="utf-8")
    assert rn._read_text_tail_chars(small, 3500) == "hello"
    assert rn._read_text_tail_chars(tmp_path / "nope.txt", 3500) == ""


def test_tail_read_split_multibyte_boundary(tmp_path):
    path = tmp_path / "emoji.txt"
    path.write_bytes(("🎉" * 5000 + "END").encode("utf-8"))

    text = rn._read_text_tail_chars(path, 100)

    # Window starts mid-emoji: at most one replacement char at the very start,
    # tail itself intact.
    assert text.endswith("🎉" * 97 + "END")
    assert text.lstrip("�").endswith("🎉" * 97 + "END")
