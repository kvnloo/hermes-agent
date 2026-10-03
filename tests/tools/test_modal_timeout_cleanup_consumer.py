"""A timed-out capture must release its local continuation before backend cleanup ends."""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from tools.environments.modal import ModalEnvironment, _AsyncWorker


def test_expired_download_releases_local_read_before_environment_cleanup(tmp_path, monkeypatch):
    worker = _AsyncWorker()
    worker.start()
    loop = worker._loop
    assert loop is not None
    read_started = threading.Event()
    read_released = threading.Event()
    terminated = threading.Event()
    gate = asyncio.Event()
    completions = []

    async def read():
        read_started.set()
        try:
            await gate.wait()
            completions.append("late body")
            return b"obsolete archive"
        finally:
            read_released.set()

    async def wait():
        completions.append("process wait")
        return 0

    async def execute(*args, **kwargs):
        return SimpleNamespace(stdout=SimpleNamespace(read=SimpleNamespace(aio=read)),
                               wait=SimpleNamespace(aio=wait))

    async def terminate():
        terminated.set()

    env = object.__new__(ModalEnvironment)
    env._worker, env._persistent, env._sync_manager = worker, False, None
    env._app = object()
    env._sandbox = SimpleNamespace(exec=SimpleNamespace(aio=execute),
                                   terminate=SimpleNamespace(aio=terminate))
    original_run = worker.run_coroutine
    submissions = []

    def run(coro, timeout=600):
        submissions.append(timeout)
        return original_run(coro, timeout=2 if len(submissions) == 1 else timeout)

    monkeypatch.setattr(worker, "run_coroutine", run)
    destination = tmp_path / "capture.tar"
    destination.write_bytes(b"existing local archive")
    try:
        with pytest.raises(TimeoutError):
            env._modal_bulk_download(destination)
        assert read_started.is_set(), "the timeout must occur inside the real capture path"
        assert destination.read_bytes() == b"existing local archive"
        env.cleanup()
        assert terminated.is_set()
        assert env._sandbox is None and env._app is None
        assert not worker._thread.is_alive()
        assert not loop.is_running()
        assert read_released.is_set(), "cleanup stopped the loop with an abandoned response read"
        assert completions == []
        assert not asyncio.all_tasks(loop), "a timed-out client continuation still owns the closed backend"
        assert submissions == [120, 15]
    finally:
        if worker._thread.is_alive():
            env.cleanup()
        # Exact old-source control leaves the read pending after stop. Drain it only
        # after assertions, on the now-stopped loop, so the test never leaks a task.
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
