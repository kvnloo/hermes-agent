"""The serving gateway, not a CLI/worker, owns its runtime status stamp (#156379)."""

import os
from types import SimpleNamespace

from gateway import run as gateway_run
from gateway import runtime_ownership, status


class _OneTick:
    def __init__(self):
        self.waited = False

    def is_set(self):
        return self.waited

    def wait(self, timeout=None):
        self.waited = True
        return True


def test_housekeeping_restamps_serving_state_but_not_draining(monkeypatch):
    writes = []
    monkeypatch.setattr(gateway_run, "_write_runtime_status_quiet", lambda **kw: writes.append(kw))
    runner = SimpleNamespace(config=None, _running=True, _draining=False,
                             _serving_state=lambda: "degraded")
    gateway_run._start_gateway_housekeeping(_OneTick(), runner=runner)
    assert writes[0].get("gateway_state") == "degraded"

    writes.clear()
    runner._draining = True
    gateway_run._start_gateway_housekeeping(_OneTick(), runner=runner)
    assert "gateway_state" not in writes[0]


def test_foreign_publisher_cannot_restamp_a_locked_gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    assert status.acquire_gateway_runtime_lock()
    try:
        assert status.write_runtime_status(gateway_state="running")
        owner = status.read_runtime_status()
        assert owner["pid"] == os.getpid()

        # A separate CLI/worker has a fresh module snapshot (default: starting)
        # and its own PID, but does not own this gateway's locked home.
        with monkeypatch.context() as foreign:
            foreign.setattr(runtime_ownership.process_ownership, "owns", lambda _home: False)
            foreign.setattr(status, "_runtime_status_state", None)
            foreign.setattr(status, "_runtime_status_state_path", None)
            foreign.setattr(status, "_build_pid_record", lambda: {
                **owner, "pid": os.getpid() + 10000, "start_time": 1,
            })
            status.publish_runtime_status(active_agents=3)
            status.write_runtime_status(gateway_state="starting")

        assert status.flush_runtime_status(timeout=2.0)
        actual = status.read_runtime_status()
        assert actual["gateway_state"] == "running"
        assert actual["pid"] == owner["pid"]
    finally:
        status.release_gateway_runtime_lock()
