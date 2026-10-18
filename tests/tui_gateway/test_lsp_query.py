"""Read-only semantic RPC admission, scope and real producer integration (#577)."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def runtime(monkeypatch, tmp_path):
    from tui_gateway import server
    from agent import lsp
    from agent.lsp import query

    transport = SimpleNamespace(write=lambda frame: True)
    owner = {"session_key": "owned", "transport": transport, "profile_home": str(tmp_path), "cwd": str(tmp_path)}
    monkeypatch.setattr(server, "_sessions", {"owned": owner})
    monkeypatch.setattr(server, "_session_is_local_backend", lambda session: True)
    monkeypatch.setattr(lsp, "get_service", lambda: None)
    producer = Mock(wraps=query.query_sync)
    monkeypatch.setattr(query, "query_sync", producer)

    def call(via=transport, **params):
        token = server.bind_transport(via)
        try:
            return server.handle_request({"id": 1, "method": "lsp.query", "params": {
                "session_id": "owned", "operation": "references", "path": "a.py", **params}})
        finally:
            server.reset_transport(token)
    return call, owner, producer


def test_real_disabled_producer_is_honest_and_never_mutates_history(runtime):
    call, owner, producer = runtime
    before = dict(owner)
    result = call()["result"]["lsp_result"]
    assert result["kind"] == "unavailable"
    assert result["path"] == owner["cwd"] + "/a.py"
    producer.assert_called_once()
    assert owner == before


def test_foreign_transport_cannot_start_lsp(runtime):
    call, _, producer = runtime
    assert "error" in call(via=SimpleNamespace(write=lambda frame: True))
    producer.assert_not_called()


@pytest.mark.parametrize("params", [{"line": 0}, {"col": True}, {"line": "2"}, {"operation": "rename"}, {"path": "../outside.py"}])
def test_invalid_query_rejected_before_producer(runtime, params):
    call, _, producer = runtime
    assert "error" in call(**params)
    producer.assert_not_called()


def test_remote_session_never_probes_local_path(runtime, monkeypatch):
    from tui_gateway import server
    call, _, producer = runtime
    monkeypatch.setattr(server, "_session_is_local_backend", lambda session: False)
    assert call()["result"]["lsp_result"]["kind"] == "unavailable"
    producer.assert_not_called()


def test_symlink_escape_is_rejected(runtime, tmp_path):
    call, _, producer = runtime
    (tmp_path / "escape").symlink_to(tmp_path.parent, target_is_directory=True)
    assert "error" in call(path="escape/outside.py")
    producer.assert_not_called()
