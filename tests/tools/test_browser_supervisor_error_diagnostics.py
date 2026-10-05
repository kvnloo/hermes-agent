"""Message-less supervisor failures retain their exception class (#133216)."""

import pytest

from tools.browser_supervisor import CDPSupervisor


@pytest.mark.parametrize("attached", [False, True])
def test_empty_timeout_identifies_failure_and_closes_supervisor_loop(
    monkeypatch, caplog, attached
):
    supervisor = CDPSupervisor("timeout-diagnostic", "ws://fixture.invalid")

    async def fail():
        if attached:
            supervisor._set_active(True)
            supervisor._ready_event.set()
        raise TimeoutError()

    monkeypatch.setattr(supervisor, "_run", fail)
    with caplog.at_level("WARNING", logger="tools.browser_supervisor"):
        if attached:
            supervisor.start(timeout=2)
        else:
            with pytest.raises(RuntimeError, match="TimeoutError"):
                supervisor.start(timeout=2)
        supervisor._thread.join(timeout=2)

    assert not supervisor._thread.is_alive()
    assert supervisor._loop.is_closed()
    assert supervisor.snapshot().active is False
    if attached:
        assert "crashed: TimeoutError" in caplog.text
