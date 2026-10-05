"""Real persisted ACP restore resolves a named custom entry (owner PR #132947)."""
import json
import socket
from types import SimpleNamespace


def test_persisted_custom_provider_restores_configured_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(
        "model:\n  provider: custom:fixture\n  default: fixture-model\n"
        "providers:\n  fixture:\n    base_url: https://fixture.invalid/v1\n"
        "    api_key: fixture-placeholder\n"
        "mcp_servers: {}\nplatform_toolsets:\n  acp: []\n", encoding="utf-8",
    )
    attempts = []

    def guard(original):
        def connect(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                attempts.append(address)
                raise AssertionError("offline restore fixture must not connect")
            return original(sock, address)
        return connect

    monkeypatch.setattr(socket.socket, "connect", guard(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guard(socket.socket.connect_ex))

    from acp_adapter.session import SessionManager
    from hermes_state import SessionDB

    captured = []

    def inert_agent(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr("run_agent.AIAgent", inert_agent)
    monkeypatch.setattr("acp_adapter.session._register_task_cwd", lambda *_: None)
    monkeypatch.setattr(
        "hermes_cli.mcp_startup.ensure_mcp_discovery_before_agent_build", lambda **_: None,
    )
    db_path = tmp_path / "state.db"
    db = SessionDB(db_path)
    try:
        previous = SessionManager(db=db)
        previous._install_state(
            "restored-fixture", SimpleNamespace(provider="custom", model="fixture-model",
                base_url="https://fixture.invalid/v1", api_mode="chat_completions"),
            str(tmp_path), "fixture-model", [{"role": "user", "content": "ordinary saved turn"}],
        )
        assert json.loads(db.get_session("restored-fixture")["model_config"])["provider"] == "custom"
    finally:
        db.close()

    reopened = SessionDB(db_path)
    try:
        restored = SessionManager(db=reopened).get_session("restored-fixture")
        assert restored is not None
        assert [(row["role"], row["content"]) for row in restored.history] == [("user", "ordinary saved turn")]
        assert len(captured) == 1
        assert captured[0]["provider"] == "custom"
        assert captured[0]["base_url"] == "https://fixture.invalid/v1"
        assert captured[0]["api_key"] == "fixture-placeholder"
        assert attempts == []
    finally:
        reopened.close()
