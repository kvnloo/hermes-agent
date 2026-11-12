"""#122813: the gateway registers a cron lifecycle persist hook so
``gateway_state.json``'s ``active_agents`` refreshes the moment a cron job
starts or ends — not only at inbound-turn boundaries (until now the file read
0 during a whole cron job with no inbound traffic, and a count written mid-job
stayed stuck until the next inbound message)."""
import cron.scheduler as sched

from tests.gateway.restart_test_helpers import make_restart_runner


def test_gateway_persists_on_cron_register_and_release(monkeypatch):
    writes = []
    monkeypatch.setattr(
        "gateway.run._write_runtime_status_quiet",
        lambda **fields: writes.append(fields))
    runner, _adapter = make_restart_runner()

    runner._register_cron_persist_hook()
    job_id = "persist-gw-test-1"
    try:
        assert sched.try_register_running_job(job_id) is True
        assert writes and writes[-1].get("active_agents") == 1
        sched.release_running_job(job_id)
        assert writes[-1].get("active_agents") == 0
    finally:
        runner._unregister_cron_persist_hook()
        sched.release_running_job(job_id)  # idempotent safety net


def test_unregister_stops_gateway_persist(monkeypatch):
    writes = []
    monkeypatch.setattr("gateway.run._write_runtime_status_quiet",
                        lambda **fields: writes.append(fields))
    runner, _adapter = make_restart_runner()
    runner._register_cron_persist_hook()
    runner._unregister_cron_persist_hook()

    job_id = "persist-gw-test-2"
    try:
        assert sched.try_register_running_job(job_id) is True
    finally:
        sched.release_running_job(job_id)
    assert writes == []


def test_register_is_idempotent(monkeypatch):
    writes = []
    monkeypatch.setattr("gateway.run._write_runtime_status_quiet",
                        lambda **fields: writes.append(fields))
    runner, _adapter = make_restart_runner()
    runner._register_cron_persist_hook()
    try:
        runner._register_cron_persist_hook()  # double register: still one callback
        job_id = "persist-gw-test-3"
        try:
            assert sched.try_register_running_job(job_id) is True
            # One notification -> one write carrying the count (not two).
            assert len([w for w in writes if "active_agents" in w]) == 1
        finally:
            sched.release_running_job(job_id)
    finally:
        runner._unregister_cron_persist_hook()

def test_cron_startup_admission_is_persisted(monkeypatch):
    """The first due job must publish its count even if ticker startup is immediate."""
    import asyncio
    from types import SimpleNamespace

    import gateway.run as gateway_run
    from cron import scheduler_provider, scheduler_thread

    writes = []
    runner, _adapter = make_restart_runner()
    monkeypatch.setattr(
        gateway_run, "_write_runtime_status_quiet",
        lambda **fields: writes.append(fields))
    monkeypatch.setattr(gateway_run, "_cron_tick_profile_homes", lambda _config: [])
    monkeypatch.setattr(gateway_run, "_start_gateway_housekeeping",
                        lambda *args, **kwargs: None)

    provider = SimpleNamespace(name="test", start=lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler_provider, "resolve_cron_scheduler",
                        lambda: provider)
    monkeypatch.setattr(scheduler_provider, "scheduler_for_profile_mode",
                        lambda scheduler, multiplex_profiles: scheduler)

    job_id = "persist-startup-admission"

    class ImmediateTicker:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            # The scheduler is permitted to admit a job before start() returns.
            assert sched.try_register_running_job(job_id) is True

    monkeypatch.setattr(scheduler_thread, "SupervisedTickerThread", ImmediateTicker)

    async def start():
        gateway_run._start_gateway_start_cron_and_housekeeping(runner)

    try:
        asyncio.run(start())
        # RED on the carrier head: ticker.start() ran before hook registration.
        assert [w["active_agents"] for w in writes] == [1]
        sched.release_running_job(job_id)
        assert [w["active_agents"] for w in writes] == [1, 0]
    finally:
        runner._unregister_cron_persist_hook()
        sched.release_running_job(job_id)
