"""Regression for NousResearch/hermes-agent#146428: recovered cron deliveries need a profile scope."""

import hashlib
import json

from agent import secret_scope
from cron import executions, scheduler, scheduler_bookkeeping
from cron.scheduler_authority import reconcile_pending
from cron.scheduler_delivery import _home_env_lookup
from gateway import session_cron
from hermes_cli import gateway_client
import hermes_constants
import tui_gateway.launch_profile_policy as launch_policy


def test_recovered_home_target_uses_firing_profile_scope(tmp_path, monkeypatch):
    """A multiplexed receipt must reach delivery with its owner's secrets, not the host's."""
    home = tmp_path / "secondary"
    admissions = home / "cron" / "admissions"
    admissions.mkdir(parents=True)
    job_id, request_id = "job-recover", "fire-recover"
    digest = hashlib.sha256(json.dumps([job_id, request_id]).encode()).hexdigest()
    (admissions / f"{digest}.json").write_text(
        json.dumps({"params": {"job_id": job_id, "request_id": request_id}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(hermes_constants, "get_hermes_home", lambda: home)
    monkeypatch.setattr(scheduler, "_get_hermes_home", lambda: str(home))
    monkeypatch.setattr(executions, "execution_owner_live", lambda *a, **k: False)
    monkeypatch.setattr(executions, "get_execution", lambda *a, **k: None)
    monkeypatch.setattr(session_cron, "owner_for_home", lambda _: None)

    # In a shared gateway the process environment can belong to another profile.
    monkeypatch.setenv("MATRIX_HOME_ROOM", "!wrong-profile:example.org")
    monkeypatch.setattr(
        launch_policy,
        "owner_secret_scope",
        lambda _: {"MATRIX_HOME_ROOM": "!secondary:example.org"},
    )

    recovered = {
        "status": "terminal",
        "job": {"id": job_id, "deliver": "origin", "origin": None},
        "result": [True, "recovered output", "recovered answer", ""],
    }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def rpc(self, method, **params):
            assert method == "cron.recover"
            assert params["request_id"] == request_id
            return recovered

    monkeypatch.setattr(gateway_client, "connect_gateway", lambda: Client())

    targets = []
    booked = []

    def capture_delivery(_delivery, _fence, _answer, _output, **_kwargs):
        # Real home-target lookup, at the same boundary the delivery lane reaches.
        targets.append(_home_env_lookup("MATRIX_HOME_ROOM"))

    def capture_booking(_delivery, _fence, execution_id, *, recovered):
        assert recovered is True
        booked.append(execution_id)
        return False  # Avoid changing the real ledger; booking was observed.

    monkeypatch.setattr(scheduler, "_save_compose_deliver", capture_delivery)
    monkeypatch.setattr(scheduler_bookkeeping, "fail_empty_response", lambda *a, **k: None)
    monkeypatch.setattr(scheduler_bookkeeping, "finish_completed_run", capture_booking)

    assert secret_scope.current_secret_scope() is None
    multiplex = secret_scope.set_multiplex_context(True)
    try:
        reconcile_pending()
    finally:
        secret_scope.reset_multiplex_context(multiplex)

    assert targets == ["!secondary:example.org"]
    assert booked == [request_id]
    assert secret_scope.current_secret_scope() is None
