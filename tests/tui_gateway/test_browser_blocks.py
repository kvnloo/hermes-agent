"""User intent and transport fences for native Tern browser blocks (#554)."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    from tui_gateway import server
    from tools import browser_tern

    transport = SimpleNamespace(write=lambda frame: True)
    owner = {"session_key": "task-owned", "transport": transport, "profile_home": tmp_path}
    monkeypatch.setattr(server, "_sessions", {"owned": owner})
    target = {"target_id": "7", "title": "Page", "url": "https://example.org/", "in_tern": True}
    provider = SimpleNamespace(listing=Mock(return_value=[]), adopt_by_user=Mock(return_value=target),
                               focus=Mock(return_value=target))
    monkeypatch.setattr(browser_tern, "get_provider", lambda: provider)

    def call(method, via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": method, "params": {"session_id": "owned", **params}})
        finally:
            server.reset_transport(token)

    return call, owner, provider


def test_user_intents_use_durable_task_owner(runtime):
    call, _, provider = runtime
    assert call("browser.blocks")["result"] == {"available": True, "blocks": []}
    assert call("browser.adopt", target_id="7")["result"]["target_id"] == "7"
    assert call("browser.focus", target_id="7")["result"]["target_id"] == "7"
    provider.listing.assert_called_once_with("task-owned")
    provider.adopt_by_user.assert_called_once_with("task-owned", "7")
    provider.focus.assert_called_once_with("task-owned", "7")


@pytest.mark.parametrize("method", ["browser.blocks", "browser.adopt", "browser.focus"])
def test_foreign_transport_is_refused(runtime, method):
    call, _, provider = runtime
    params = {} if method == "browser.blocks" else {"target_id": "7"}
    assert "error" in call(method, via=SimpleNamespace(write=lambda f: True), **params)
    provider.listing.assert_not_called()
    provider.adopt_by_user.assert_not_called()
    provider.focus.assert_not_called()


@pytest.mark.parametrize("target_id", ["07", " 7", "7x", "+7", "", True, 7])
def test_malformed_target_refused_before_side_effects(runtime, target_id):
    call, _, provider = runtime
    assert "error" in call("browser.adopt", target_id=target_id)
    provider.adopt_by_user.assert_not_called()


def test_busy_session_cannot_be_retargeted(runtime):
    call, owner, provider = runtime
    owner["running"] = True
    assert "error" in call("browser.adopt", target_id="7")
    provider.adopt_by_user.assert_not_called()


def test_unavailable_discovery_preserves_legacy_backend(runtime, monkeypatch):
    from tools import browser_tern
    call, _, _ = runtime
    monkeypatch.setattr(browser_tern, "get_provider", lambda: None)
    assert call("browser.blocks")["result"] == {"available": False, "blocks": []}
    assert "error" in call("browser.adopt", target_id="7")
