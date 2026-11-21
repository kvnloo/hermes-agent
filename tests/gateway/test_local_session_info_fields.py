"""``session.info`` carries what main's classic CLI read off itself for /status, the status bar and the
exit summary (wave A2): title, started/last-active times, yolo, api_mode, tool_count and a masked
credential hint (never the key); re-published when the auto-title lands."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from gateway.config import Platform


@pytest.mark.asyncio
async def test_session_info_carries_the_classic_cli_fields(tmp_path, monkeypatch):
    from gateway.session_contract import SessionRef
    from gateway.session_local import local_session_info
    from tests.gateway.test_surface_admission import _authority

    async def answer(event):
        return 'ok'
    authority = await _authority(tmp_path, monkeypatch, answer)
    agent = SimpleNamespace(model='m', provider='custom', api_mode='chat_completions',
                            api_key='sk-abcdefghijklmnop1234', tools=[{'function': {'name': 'a'}}] * 3)
    authority.runner._cached_agent_for = lambda route: agent
    authority.db.set_session_title('s', 'Some Title')
    info = local_session_info(authority, SessionRef('p', 's'))
    assert info['title'] == 'Some Title'
    assert isinstance(info['started_at'], float) and isinstance(info['last_active_at'], float)
    assert info['yolo'] is False and info['api_mode'] == 'chat_completions' and info['tool_count'] == 3
    assert info['credential_hint'] == 'sk-a...1234' and 'abcdefgh' not in str(info)
    from tui_gateway.contracts.registry import CANONICAL_METHODS
    CANONICAL_METHODS['session.info'].result.model_validate(
        {**info, 'profile_name': 'default', 'desktop_protocol': 'hermes-gateway-v1', 'lazy': False})


@pytest.mark.asyncio
async def test_gateway_session_info_exposes_the_frozen_terminal_backend(tmp_path, monkeypatch):
    """A Desktop/Webapp viewer gets its session's backend, not the gateway host's."""
    import json
    from dataclasses import replace

    from gateway.session_local import create_local_session, local_session_info
    from tests.gateway.test_local_post_delivery import _owner, _viewer
    from tui_gateway.contracts.registry import CANONICAL_METHODS

    runner, authority, db = await _owner(tmp_path, monkeypatch)
    try:
        ref = create_local_session(authority, _viewer(), {
            'request_id': 'backend', 'source': 'tui', 'model': 'fixture', 'toolsets': []})
        source = authority.sessions[ref.session_id].source
        policies = runner.adapters[Platform.LOCAL].policies
        policy = policies[source.chat_id]
        monkeypatch.setenv('TERMINAL_ENV', 'ssh')  # gateway process is not this session's policy

        for backend in ('local', 'docker'):
            policies[source.chat_id] = replace(
                policy, terminal_json=json.dumps({
                    **json.loads(policy.terminal_json), 'TERMINAL_ENV': backend}))
            info = local_session_info(authority, ref)
            assert info['terminal_backend'] == backend
            assert CANONICAL_METHODS['session.info'].result.model_validate(info).terminal_backend == backend
    finally:
        db.close()

def test_local_viewer_title_republishes_session_info(monkeypatch):
    from gateway.run_turn_runner import TurnRunner
    published = []
    live = SimpleNamespace(event_stream=SimpleNamespace(
        publish=lambda sid, payload, event_type: published.append((event_type, payload))))
    authority = SimpleNamespace(sessions={'s': live})
    turn = object.__new__(TurnRunner)
    turn._ctx = SimpleNamespace(source=SimpleNamespace(platform=Platform.LOCAL), session_key='k')
    turn._approval_owner = (authority, 's', 1)
    turn._runner = SimpleNamespace(_recover_discord_auto_thread_source=lambda source, key: source,
                                   _is_telegram_topic_lane=lambda s: False,
                                   _is_discord_auto_thread_lane=lambda s: False,
                                   _is_relay_discord_channel_lane=lambda s: False)
    from gateway import session_local
    monkeypatch.setattr(session_local, 'local_session_info', lambda authority, ref: {'title': 'Auto'})
    agent = SimpleNamespace(session_id='s')
    turn._attach_session_title_callback(agent, turn._ctx)
    agent._on_session_title('Auto', 'llm')
    assert published == [('session.info', {'title': 'Auto'})]
