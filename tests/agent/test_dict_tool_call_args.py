import json
import socket
from types import SimpleNamespace


def _tool_call(name: str, arguments):
    return SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _response_with_tool_call(arguments):
    assistant = SimpleNamespace(
        content=None,
        reasoning=None,
        tool_calls=[_tool_call("read_file", arguments)],
    )
    choice = SimpleNamespace(message=assistant, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice], usage=None)


def test_tool_call_validation_accepts_dict_arguments(monkeypatch, tmp_path):
    from run_agent import AIAgent
    from tools.registry import registry

    monkeypatch.setattr("agent.process_bootstrap.OpenAI", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(
        "model_tools.get_tool_definitions",
        lambda *args, **kwargs: [{"type": "function", "function": registry.get_schema("read_file")}],
    )

    received = []

    def inert_read(args, **_kwargs):
        received.append(dict(args))
        return json.dumps({"ok": True, "args": args})

    monkeypatch.setattr(registry.get_entry("read_file"), "handler", inert_read)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text(
        "environment_probe: false\nlocal_runtime:\n  enabled: false\n"
        "model:\n  context_length: 128000\n", encoding="utf-8",
    )
    monkeypatch.setattr("agent.model_metadata.detect_local_server_type", lambda *args, **kwargs: "unknown")
    network_attempts = []

    def deny_network(original):
        def guarded(sock, address):
            if sock.family in (socket.AF_INET, socket.AF_INET6):
                network_attempts.append(address)
                raise AssertionError("fixture must not connect to a network service")
            return original(sock, address)
        return guarded

    monkeypatch.setattr(socket.socket, "connect", deny_network(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", deny_network(socket.socket.connect_ex))

    agent = AIAgent(
        model="test-model",
        provider="custom",
        api_mode="chat_completions",
        api_key="test-key",
        base_url="http://localhost:8080/v1",
        platform="cli",
        max_iterations=3,
        quiet_mode=True,
        skip_memory=True,
    )
    agent._disable_streaming = True

    try:
        message = _response_with_tool_call({"path": "README.md"}).choices[0].message
        messages = []
        agent._execute_tool_calls(message, messages, "inert-dict-fixture")
        assert received == [{"path": "README.md"}]
        assert network_attempts == []
    finally:
        agent.close()


def test_tool_call_argument_parser_accepts_structured_values():
    from agent.tool_executor import _parse_tool_arguments

    args, error = _parse_tool_arguments({"action": "send", "target": "telegram:user", "message": "Test"})

    assert error is None
    assert args == {"action": "send", "target": "telegram:user", "message": "Test"}

    args, error = _parse_tool_arguments(["telegram:user", "Test"])

    assert args == {}
    assert error is not None
