"""A stalled relay roster fsync must not freeze the canonical gateway (#149652)."""

import asyncio
from contextvars import ContextVar
import os
import threading
from types import SimpleNamespace

from gateway.session_controls import AuthorityConnection


def test_roster_fsync_does_not_block_gateway_loop(monkeypatch, tmp_path):
    from gateway import session_authorities, session_bot

    # Exercise the real relay operation and atomic JSON writer, without starting
    # a gateway service or a database just to satisfy the owner admission gates.
    monkeypatch.setattr(session_authorities, "require_serving", lambda authority: None)
    monkeypatch.setattr(session_authorities, "served_profile_name", lambda home: "default")
    monkeypatch.setattr(session_bot, "_home", lambda *args: None)
    connection = SimpleNamespace(
        authority=SimpleNamespace(db=SimpleNamespace(db_path=str(tmp_path / "state.db"))),
        actor=SimpleNamespace(capabilities={"session:control"}),
    )
    entered, release = threading.Event(), threading.Event()
    owner_context = ContextVar("relay_test_owner_home", default=None)
    fsync_threads, fsync_owners = [], []
    real_fsync = os.fsync

    def stalled_fsync(fd):
        fsync_threads.append(threading.get_ident())
        fsync_owners.append(owner_context.get())
        entered.set()
        if not release.wait(timeout=5):
            raise AssertionError("the gateway loop could not release a stalled fsync")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", stalled_fsync)

    async def exercise():
        loop_thread = threading.get_ident()
        token = owner_context.set("served-home")
        task = asyncio.create_task(
            AuthorityConnection.bot_roster(connection, None, {"agents": []}))
        try:
            assert await asyncio.wait_for(asyncio.to_thread(entered.wait, 4), timeout=5)
            assert not task.done()  # fsync is still deliberately held
            tick = asyncio.Event()
            asyncio.get_running_loop().call_soon(tick.set)
            await asyncio.wait_for(tick.wait(), timeout=4)
        finally:
            release.set()
            owner_context.reset(token)
        result = await asyncio.wait_for(task, timeout=5)
        assert fsync_threads and all(t != loop_thread for t in fsync_threads)
        return result

    assert asyncio.run(exercise()) == {"count": 0}
    assert fsync_owners and all(value == "served-home" for value in fsync_owners)
    assert (tmp_path / "bot_relay" / "roster.json").is_file()
