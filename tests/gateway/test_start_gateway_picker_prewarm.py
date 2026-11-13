"""Gateway and standalone dashboard startup prewarm the picker without waiting (#647)."""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from gateway import run
from tests.gateway.test_bootstrap_deferred_integrity_scan import _startup


@pytest.fixture
def blocked_prewarm(monkeypatch):
    from hermes_cli import inventory, model_switch, model_switch_providers

    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    threads = []

    def warm(**kwargs):
        entered.set()
        release.wait(30)
        finished.set()
        return []

    monkeypatch.setattr(model_switch_providers, "_picker_prewarm_done", threading.Event())
    monkeypatch.setattr(inventory, "load_picker_context", lambda: SimpleNamespace(
        current_provider="", current_base_url="", current_model="",
        user_providers={}, custom_providers=[], excluded_providers=[]))
    monkeypatch.setattr(model_switch, "list_authenticated_providers", warm)
    prewarm = model_switch_providers.prewarm_picker_cache_async

    def start():
        thread = prewarm()
        if thread is not None:
            threads.append(thread)
        return thread

    scheduled = Mock(side_effect=start)
    monkeypatch.setattr(model_switch_providers, "prewarm_picker_cache_async", scheduled)
    yield SimpleNamespace(scheduled=scheduled, entered=entered, finished=finished, threads=threads)
    release.set()
    for thread in threads:
        thread.join(timeout=5)
        assert not thread.is_alive()


def _assert_prewarm_is_still_running(prewarm):
    prewarm.scheduled.assert_called_once_with()
    assert prewarm.entered.wait(5), "startup did not start the picker worker"
    assert not prewarm.finished.is_set(), "startup waited for the picker worker"
    assert prewarm.threads[0].is_alive()


@pytest.mark.asyncio
async def test_start_gateway_prewarms_picker_cache(_startup, blocked_prewarm):
    from gateway.config import GatewayConfig

    assert await asyncio.wait_for(run.start_gateway(GatewayConfig(), verbosity=None), 30) is True
    _assert_prewarm_is_still_running(blocked_prewarm)


@pytest.fixture
def dashboard(monkeypatch):
    from hermes_cli import free_tier_bootstrap, process_identity, web_server
    from hermes_cli.local_runtime import bootstrap
    from tui_gateway import methods_groups, server

    monkeypatch.setattr(web_server, "_warm_gateway_module", lambda: None)
    monkeypatch.setattr(web_server, "_eager_reconcile_own_session_db", lambda: None)
    monkeypatch.setattr(methods_groups, "start_hosted_room_service", lambda: None)
    monkeypatch.setattr(methods_groups, "stop_hosted_room_service", lambda **kwargs: None)
    monkeypatch.setattr(server, "install_tui_message_injector", lambda: None)
    monkeypatch.setattr(server, "clear_tui_message_injector", lambda: None)
    monkeypatch.setattr(process_identity, "is_desktop_owned_backend", lambda: False)
    monkeypatch.setattr(bootstrap, "ensure_local_runtime", lambda config: None)
    monkeypatch.setattr(bootstrap, "shutdown_local_runtime", lambda: None)
    monkeypatch.setattr(free_tier_bootstrap, "start_background_bootstrap", lambda: None)
    for name, value in {"bound_host": "localhost", "auth_required": False,
                        "ui_surface": "dashboard", "gateway_runner": None}.items():
        monkeypatch.setattr(web_server.app.state, name, value, raising=False)
    return web_server.app


def test_web_server_lifespan_prewarms_picker_cache(dashboard, blocked_prewarm):
    from hermes_cli import web_server

    with TestClient(dashboard, base_url="http://localhost") as client:
        _assert_prewarm_is_still_running(blocked_prewarm)
        response = client.get("/api/dashboard/themes", headers={
            web_server._SESSION_HEADER_NAME: web_server._SESSION_TOKEN})
        assert response.status_code == 200, response.text
        assert not blocked_prewarm.finished.is_set()


def test_gateway_owned_dashboard_does_not_schedule_a_second_prewarm(dashboard, blocked_prewarm, monkeypatch):
    monkeypatch.setattr(dashboard.state, "gateway_runner", object(), raising=False)
    monkeypatch.setattr(dashboard.state, "ui_surface", "gateway", raising=False)
    async def enter():
        async with dashboard.router.lifespan_context(dashboard):
            blocked_prewarm.scheduled.assert_not_called()
    asyncio.run(enter())
