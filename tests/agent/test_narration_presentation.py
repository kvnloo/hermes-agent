"""Provider-shaped regression for connector narration (#592). No live provider calls."""
import base64
import copy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent.narration import is_narration_signature, reasoning_presentation
from agent.transports.anthropic import AnthropicTransport
from agent.transports.bedrock import BedrockTransport


def signature(kind):
    # Actual v4 protobuf layout used by OMP's stream fixture, including opaque tail.
    header = b'\x08\x11\x18\x02\x38\x01\x42' + bytes([len(kind)]) + kind.encode()
    envelope = b'\x0a' + bytes([len(header)]) + header + b'\x12\x03abc'
    return base64.b64encode(b'\x08\x04\x12' + bytes([len(envelope)]) + envelope).decode()


@pytest.mark.parametrize('kind,expected', [('narration', True), ('thinking', False), ('Narration', False), ('narrationx', False)])
def test_exact_signature_kind(kind, expected):
    assert is_narration_signature(signature(kind)) is expected


@pytest.mark.parametrize('bad', ['', 'not base64!', base64.b64encode(b'\x12\xff\xff\xff\xff\x0f').decode(),
                                      base64.b64encode(b'\x88\x80\x80\x80\x80\x00').decode()])
def test_unknown_or_malformed_is_never_promoted(bad):
    assert not is_narration_signature(bad)


@pytest.mark.parametrize('provider', ['anthropic', 'bedrock'])
def test_producer_and_history_preserve_signed_replay_but_project_narration(provider, monkeypatch):
    from agent.chat_completion_helpers import build_assistant_message
    from tui_gateway import server

    thought, narration = 'Private deliberation.', 'I found the cause; checking the fix.'
    segments = [(thought, signature('thinking')), (narration, signature('narration'))]
    if provider == 'anthropic':
        raw = SimpleNamespace(content=[SimpleNamespace(type='thinking', thinking=text, signature=sig)
                                       for text, sig in segments], stop_reason='end_turn', stop_details=None)
        response = AnthropicTransport().normalize_response(raw)
    else:
        raw = {'output': {'message': {'role': 'assistant', 'content': [
            {'reasoningContent': {'reasoningText': {'text': text, 'signature': sig}}} for text, sig in segments
        ]}}, 'stopReason': 'end_turn', 'usage': {}}
        response = BedrockTransport().normalize_response(raw)
    before = copy.deepcopy(response.provider_data)
    agent = SimpleNamespace(_extract_reasoning=lambda m: m.reasoning, verbose_logging=False,
                            reasoning_callback=Mock(), stream_delta_callback=Mock(), _stream_callback=None,
                            tool_progress_callback=Mock(), _strip_think_blocks=lambda text: text)
    stored = build_assistant_message(agent, response, 'stop')
    expected = [{'text': thought, 'narration': False}, {'text': narration, 'narration': True}]
    assert reasoning_presentation(stored) == expected
    assert response.provider_data == before
    agent.reasoning_callback.assert_not_called()  # stream wasn't duplicated
    event = agent.tool_progress_callback.call_args
    assert event.args[0] == 'reasoning.available'
    assert event.kwargs['presentation'] == expected
    history = copy.deepcopy(stored)
    projected = server._history_to_messages([stored])
    assert projected[0]['reasoning_presentation'] == expected
    assert stored == history
    emitted = []
    monkeypatch.setattr(server, '_session_show_reasoning', lambda sid: False)
    monkeypatch.setattr(server, '_session_verbose', lambda sid: False)
    monkeypatch.setattr(server, '_emit', lambda *args: emitted.append(args))
    server._on_tool_progress('s', *event.args, **event.kwargs)
    assert emitted[-1] == ('reasoning.available', 's', {'text': '', 'presentation': [expected[1]]})
