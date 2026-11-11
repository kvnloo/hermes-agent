"""The gateway writes heap snapshots on SIGRTMIN+3, so a live leak can be attributed without ptrace."""
import os
import signal
import tracemalloc

import pytest

from gateway import heap_diag


@pytest.mark.skipif(heap_diag.heap_signal() is None, reason="no realtime signals")
def test_signal_starts_tracing_then_snapshots_and_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HEAP_DIAG_DIR", str(tmp_path / "heap"))
    previous = signal.getsignal(heap_diag.heap_signal())
    try:
        assert heap_diag.install(tmp_path)
        os.kill(os.getpid(), heap_diag.heap_signal())
        assert tracemalloc.is_tracing()
        hoard = [bytearray(1024) for _ in range(2000)]  # ~2 MB the diff must attribute to this line
        (tmp_path / "heap" / "stop").write_text("")
        os.kill(os.getpid(), heap_diag.heap_signal())
        assert not tracemalloc.is_tracing()
        first = tracemalloc.Snapshot.load(str(tmp_path / "heap" / "snap-0.tm"))
        second = tracemalloc.Snapshot.load(str(tmp_path / "heap" / "snap-1.tm"))
        top = second.compare_to(first, "lineno")[0]
        assert top.traceback[0].filename == __file__ and top.size_diff > 1_500_000
        assert (tmp_path / "heap" / "census-1.json").exists()
        del hoard
    finally:
        signal.signal(heap_diag.heap_signal(), previous)
        if tracemalloc.is_tracing():
            tracemalloc.stop()
