"""On-demand heap attribution for a live gateway, without ptrace.

``kill -SIGRTMIN+3 <gateway pid>``: the first signal starts tracemalloc and writes ``snap-0.tm``;
each later one writes the next ``snap-N.tm`` plus a ``census-N.json`` object-type count, and a
``stop`` file in the directory stops tracing after that snapshot. Compare two snapshots with
``tracemalloc.Snapshot.load(...).compare_to(...)``. Zero cost until signalled. The directory is
``HERMES_HEAP_DIAG_DIR`` or ``<hermes home>/logs/heap``. Yama (ptrace_scope=1) blocks
``sys.remote_exec``/memray attach on the gateway, which is why this lives in-process.
"""
import collections
import gc
import json
import logging
import os
import signal
import time
import tracemalloc
from pathlib import Path

logger = logging.getLogger(__name__)
FRAMES = 8


def heap_signal():
    rtmin = getattr(signal, "SIGRTMIN", None)
    return None if rtmin is None else rtmin + 3


def snapshot(directory: Path) -> Path:
    """Start tracing (first call) and write the next snapshot; returns the snapshot path."""
    directory.mkdir(parents=True, exist_ok=True)
    n = sum(1 for _ in directory.glob("snap-*.tm"))
    if not tracemalloc.is_tracing():
        tracemalloc.start(FRAMES)
    gc.collect()
    census = collections.Counter(type(o).__name__ for o in gc.get_objects())
    (directory / f"census-{n}.json").write_text(json.dumps(
        {"ts": time.time(), "pid": os.getpid(), "traced": tracemalloc.get_traced_memory(),
         "top": census.most_common(80)}))
    path = directory / f"snap-{n}.tm"
    tracemalloc.take_snapshot().dump(str(path))
    if (directory / "stop").exists():
        tracemalloc.stop()
    logger.warning("heap diag: wrote %s (tracing=%s)", path, tracemalloc.is_tracing())
    return path


def install(hermes_home) -> bool:
    """Register the heap-snapshot signal (main thread only). False when the platform has none."""
    sig = heap_signal()
    if sig is None:
        return False
    directory = Path(os.environ.get("HERMES_HEAP_DIAG_DIR") or Path(hermes_home) / "logs" / "heap")

    def _handler(_signum, _frame):
        try:
            snapshot(directory)
        except Exception:
            logger.warning("heap diag snapshot failed", exc_info=True)

    signal.signal(sig, _handler)
    return True
