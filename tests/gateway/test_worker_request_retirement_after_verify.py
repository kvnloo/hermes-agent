"""A retired owner cannot accept a worker write after off-loop verification.

The claim/verify wait introduced for #145022 allows retirement to race with
adopt and persist; the original gateway epoch stays valid until replacement.
"""

import asyncio
import threading
from types import SimpleNamespace

import pytest

from gateway import session_worker
from hermes_state_runtime import RuntimeStoreError


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["adopt", "persist"])
async def test_worker_request_rechecks_retirement_after_verification(monkeypatch, operation):
    loop = asyncio.get_running_loop()
    loop_thread = threading.get_ident()
    verifying = asyncio.Event()
    release = threading.Event()
    authority = SimpleNamespace(profile_id="profile", epoch=7, db=object(), retired=False)
    actor = SimpleNamespace(capabilities=frozenset({"worker:adopt"}))
    connection = SimpleNamespace(authority=authority, actor=actor)
    params = {key: "x" for key in session_worker._SCOPE}
    if operation == "persist":
        params.update(epoch=7, sequence=1, operation="execution.start", payload={})

    monkeypatch.setattr(session_worker, "_claim", lambda *args: "claim")

    def blocked_verify(*args):
        assert threading.get_ident() != loop_thread, "_verify blocked the event loop"
        loop.call_soon_threadsafe(verifying.set)
        assert release.wait(10), "verification was never released"

    def unexpected_write(*args, **kwargs):
        pytest.fail("worker write reached the retired authority")

    monkeypatch.setattr(session_worker, "_verify", blocked_verify)
    monkeypatch.setattr(session_worker, "adopt_worker_execution", unexpected_write)
    monkeypatch.setattr(session_worker, "mutate_worker_execution", unexpected_write)

    request = asyncio.create_task(
        session_worker.worker_request(connection, "ref", params, operation=operation)
    )
    entered = asyncio.create_task(verifying.wait())
    try:
        done, _ = await asyncio.wait(
            {entered, request}, timeout=5, return_when=asyncio.FIRST_COMPLETED
        )
        if request in done:
            await request
        assert entered in done, "worker verification did not begin"
        authority.retired = True
        release.set()
        with pytest.raises(RuntimeStoreError, match="runtime_retired"):
            await asyncio.wait_for(request, timeout=5)
    finally:
        release.set()
        entered.cancel()
        await asyncio.gather(entered, return_exceptions=True)
        if not request.done():
            request.cancel()
        await asyncio.gather(request, return_exceptions=True)
