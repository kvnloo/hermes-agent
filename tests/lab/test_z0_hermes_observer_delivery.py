"""Observer storage stalls must never reach the agent loop.

The host fails a ``pre_tool_call`` callback closed once it outlives
``plugins.hook_callback_timeout`` and runs ``subagent_stop`` callbacks on the caller
thread with no timeout at all.  An observer that writes to disk inside those hooks turns
a hung filesystem into blocked tools or a hung parent process.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from hermes_cli.plugins import PluginManager
from hermes_constants import reset_hermes_home_override, set_hermes_home_override

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "lab" / "z0_hermes_observer" / "__init__.py"
DEADLINE = 5.0  # seconds; deliberately generous so a loaded CI runner cannot flake


def _load():
    spec = importlib.util.spec_from_file_location("z0_hermes_observer_delivery_plugin", PLUGIN)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _host_with_observer(module) -> PluginManager:
    """A real PluginManager with the observer registered the way discovery registers it."""
    manager = PluginManager()

    class Ctx:
        def register_hook(self, name, callback):
            manager._hooks.setdefault(name, []).append(callback)

    module.register(Ctx())
    return manager


def _within(seconds, fn, *args, **kwargs):
    """Run *fn* on a helper thread; fail instead of hanging the suite if it outlives *seconds*."""
    box: dict = {}

    def run():
        try:
            box["result"] = fn(*args, **kwargs)
        except BaseException as exc:  # re-raised on the test thread
            box["error"] = exc

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)
    assert not worker.is_alive(), f"{getattr(fn, '__name__', fn)} still blocked after {seconds}s"
    if "error" in box:
        raise box["error"]
    return box["result"]


def _stall_the_writer(module) -> None:
    """Emit one row and wait until the writer holds it, stuck on the stalled spool."""
    _within(DEADLINE, module.observe, "on_session_start", session_id="s")
    deadline = time.monotonic() + DEADLINE
    while _within(DEADLINE, module.stats)["inflight"] != 1:
        assert time.monotonic() < deadline, "the writer never picked the row up"
        time.sleep(0.01)


class _StalledStorage:
    """A spool on a FIFO nobody reads: every open() blocks, like a hung filesystem."""

    def __init__(self, path: Path):
        self.path = path
        os.mkfifo(path)
        self._reader = -1

    def recover(self) -> None:
        """Attach a reader so blocked writers get through."""
        if self._reader < 0:
            self._reader = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)

    def rows(self) -> list[dict]:
        chunks = []
        while True:
            try:
                chunk = os.read(self._reader, 65536)
            except BlockingIOError:
                break
            if not chunk:
                break
            chunks.append(chunk)
        return [json.loads(line) for line in b"".join(chunks).decode("utf-8").splitlines()]

    def close(self) -> None:
        self.recover()  # never leave a writer thread blocked behind a failed test
        os.close(self._reader)


@pytest.fixture
def stalled_storage(tmp_path, monkeypatch):
    stall = _StalledStorage(tmp_path / "events.jsonl")
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(stall.path))
    yield stall
    stall.close()


@pytest.mark.platforms("posix")
def test_stalled_storage_does_not_block_tool_calls(stalled_storage, monkeypatch):
    monkeypatch.setattr("hermes_cli.plugins._resolve_hook_callback_timeout", lambda: 0.3)
    module = _load()
    host = _host_with_observer(module)
    _stall_the_writer(module)

    results = _within(
        DEADLINE, host.invoke_hook, "pre_tool_call",
        tool_name="terminal", args={}, session_id="s", turn_id="t", tool_call_id="c1",
    )

    assert results == []  # a timed-out pre_tool_call callback would have produced a block directive

    stalled_storage.recover()
    assert module.flush(DEADLINE)
    assert [row["event"] for row in stalled_storage.rows()] == ["on_session_start", "pre_tool_call"]


@pytest.mark.platforms("posix")
def test_stalled_storage_does_not_hang_the_caller_of_subagent_stop(stalled_storage):
    module = _load()
    host = _host_with_observer(module)
    _stall_the_writer(module)

    _within(
        DEADLINE, host.invoke_hook, "subagent_stop",
        parent_session_id="p", parent_turn_id="t", child_session_id="c",
        child_role="leaf", child_status="completed", duration_ms=5, tool_call_history=[],
    )

    stalled_storage.recover()
    assert module.flush(DEADLINE)
    assert [row["event"] for row in stalled_storage.rows()] == ["on_session_start", "subagent_stop"]


def test_rows_beyond_the_buffer_are_counted_and_reported_after_recovery(tmp_path, monkeypatch):
    spool = tmp_path / "events.jsonl"
    monkeypatch.setenv("Z0INT_HERMES_EVENT_PATH", str(spool))
    module = _load()
    monkeypatch.setattr(module, "_MAX_PENDING", 3)
    entered, release = threading.Event(), threading.Event()
    real_append = module._append

    def stalled_append(path, lines):
        entered.set()
        assert release.wait(2 * DEADLINE)
        real_append(path, lines)

    monkeypatch.setattr(module, "_append", stalled_append)

    def observe(i):
        module.observe("pre_api_request", session_id="s", turn_id="t", api_request_id=f"r{i}")

    observe(0)
    assert entered.wait(DEADLINE)  # the writer now holds r0 inside the stalled append
    for i in range(1, 8):
        observe(i)
    assert module.stats() == {"pending": 3, "inflight": 1, "dropped": 4}

    release.set()
    assert module.flush(DEADLINE)

    rows = [json.loads(line) for line in spool.read_text(encoding="utf-8-sig").splitlines()]
    assert [row["identity"].get("api_request_id") for row in rows] == ["r0", None, "r1", "r2", "r3"]
    assert rows[1]["event"] == "observer_rows_dropped"
    assert rows[1]["fields"] == {"dropped_rows": 4}
    assert module.stats()["dropped"] == 0


def test_rows_follow_the_profile_bound_when_they_were_observed(tmp_path, monkeypatch):
    monkeypatch.delenv("Z0INT_HERMES_EVENT_PATH", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "launch"))
    module = _load()
    homes = {"a": tmp_path / "a", "b": tmp_path / "b"}

    for name in ("a", "b", "a"):  # one process serving several profiles, A -> B -> A
        token = set_hermes_home_override(homes[name])
        try:
            module.observe("pre_api_request", session_id=name, turn_id="t")
        finally:
            reset_hermes_home_override(token)
    assert module.flush(DEADLINE)

    def sessions(home: Path) -> list[str]:
        spool = home / "plugin-data" / "z0-hermes-observer" / "events.jsonl"
        return [json.loads(line)["identity"]["session_id"] for line in spool.read_text(encoding="utf-8-sig").splitlines()]

    assert sessions(homes["a"]) == ["a", "a"]
    assert sessions(homes["b"]) == ["b"]
    assert not (tmp_path / "launch" / "plugin-data").exists()


_EXIT_PROBE = """
import importlib.util, os, sys, time

spec = importlib.util.spec_from_file_location("z0_hermes_observer_exit_probe", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if os.environ.get("PROBE_SLOW_STORAGE"):
    real_append = module._append

    def slow_append(path, lines):
        time.sleep(0.5)
        real_append(path, lines)

    module._append = slow_append
for i in range(50):
    module.observe("pre_api_request", session_id="s", turn_id="t", api_request_id=f"r{i}")
"""


def _run_probe(spool: Path, timeout: float, **env_extra: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "Z0INT_HERMES_EVENT_PATH": str(spool), **env_extra}
    return subprocess.run(
        [sys.executable, "-c", _EXIT_PROBE, str(PLUGIN)],
        cwd=ROOT, env=env, timeout=timeout, capture_output=True, text=True, check=False,
    )


def test_rows_still_pending_at_interpreter_exit_are_written(tmp_path):
    spool = tmp_path / "events.jsonl"

    done = _run_probe(spool, timeout=60, PROBE_SLOW_STORAGE="1")

    assert done.returncode == 0, done.stderr
    ids = [json.loads(line)["identity"]["api_request_id"] for line in spool.read_text(encoding="utf-8-sig").splitlines()]
    assert ids == [f"r{i}" for i in range(50)]


@pytest.mark.platforms("posix")
def test_stalled_storage_cannot_keep_the_process_from_exiting(tmp_path):
    spool = tmp_path / "events.jsonl"
    os.mkfifo(spool)

    done = _run_probe(spool, timeout=30)  # TimeoutExpired here means the process wedged on the stall

    assert done.returncode == 0, done.stderr
