"""`hermes acp` launch flags freeze into the gateway session they create (#134889 ACP-13)."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from acp_adapter.gateway_server import GatewayACPAgent

_ENV = ('HERMES_YOLO_MODE', 'HERMES_SAFE_MODE', 'HERMES_IGNORE_USER_CONFIG', 'HERMES_IGNORE_RULES',
        'HERMES_ACCEPT_HOOKS', 'HERMES_MODEL', 'HERMES_INFERENCE_MODEL', 'HERMES_INFERENCE_PROVIDER')
_FLAGS = ('yolo', 'safe_mode', 'ignore_user_config', 'ignore_rules', 'accept_hooks')


def _agent(created):
    async def rpc(method, _timeout=None, **params):  # local client deadline is not sent to the owner
        if method == 'runtime.describe':
            return {'session_create': {'sources': ['acp']}, 'capabilities': ['acp-editor-policy-v1']}
        if method == 'config.set':  # the new session's live-reasoning flag (#134889 ACP-4)
            return {'key': params['key'], 'value': params['value'], 'scope': 'session'}
        assert method == 'session.create', method
        created.append(params)
        return {'session_id': 's', 'info': {'cwd': params['cwd']}}

    agent = GatewayACPAgent()
    agent._gateway = AsyncMock()
    agent._gateway.rpc.side_effect = rpc
    agent._session_fields = AsyncMock(return_value={})
    return agent


@pytest.mark.asyncio
async def test_launch_env_rides_session_create(monkeypatch, tmp_path):
    for name in _ENV[:5]:
        monkeypatch.setenv(name, '1')
    monkeypatch.setenv('HERMES_MODEL', 'explicit-model')  # a bypass session needs a route (below)
    monkeypatch.setenv('HERMES_INFERENCE_PROVIDER', 'openrouter')
    created = []
    await _agent(created).new_session(cwd=str(tmp_path))
    assert {k: created[0].get(k) for k in _FLAGS} == dict.fromkeys(_FLAGS, True)


@pytest.mark.asyncio
async def test_safe_mode_acp_session_freezes_the_launch_model(monkeypatch, tmp_path):
    """`hermes -m <model> --provider <name> --safe-mode acp`: the owner reads no profile default, so the
    launch's model rides session.create and the owner's bypass policy accepts it."""
    for name in _ENV:
        monkeypatch.setenv(name, '')  # recorded, so cmd_acp's exports are undone after the test
    monkeypatch.setenv('HERMES_SAFE_MODE', '1')  # what main() exports for --safe-mode
    monkeypatch.setenv('HERMES_IGNORE_USER_CONFIG', '1')
    import acp_adapter.entry
    from gateway.session_local import _bypass_policy
    from hermes_cli.main_agent_cmds import cmd_acp
    monkeypatch.setattr(acp_adapter.entry, 'main', lambda argv: None)
    cmd_acp(SimpleNamespace(model='anthropic/claude-sonnet-4', provider='openrouter'))
    created = []
    await _agent(created).new_session(cwd=str(tmp_path))
    params = created[0]
    assert (params['model'], params['provider'], params['safe_mode']) == ('anthropic/claude-sonnet-4', 'openrouter', True)
    frozen = _bypass_policy({k: v for k, v in params.items() if k != 'request_id'}, private_secrets={})
    assert frozen.model == 'anthropic/claude-sonnet-4' and frozen.safe_mode


@pytest.mark.asyncio
@pytest.mark.parametrize('flag', ['HERMES_SAFE_MODE', 'HERMES_IGNORE_USER_CONFIG'])
async def test_bypass_without_a_model_names_the_missing_flag(monkeypatch, tmp_path, flag):
    from hermes_cli.gateway_client import GatewayClientError
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(flag, '1')
    created = []
    with pytest.raises(GatewayClientError, match='hermes -m <model>'):
        await _agent(created).new_session(cwd=str(tmp_path))
    assert created == []


@pytest.mark.asyncio
@pytest.mark.parametrize('flag', ['HERMES_SAFE_MODE', 'HERMES_IGNORE_USER_CONFIG'])
async def test_bypass_with_a_model_but_no_provider_is_refused_at_session_new(monkeypatch, tmp_path, flag):
    """`hermes -m <model> --safe-mode acp`: the owner would accept the session, then its first turn
    could not build the agent. Refused before session.create, naming the missing flag."""
    from hermes_cli.gateway_client import GatewayClientError
    for name in _ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(flag, '1')
    monkeypatch.setenv('HERMES_MODEL', 'gpt-4o-mini')
    created = []
    with pytest.raises(GatewayClientError, match='launch with --provider too'):
        await _agent(created).new_session(cwd=str(tmp_path))
    assert created == []


@pytest.mark.asyncio
async def test_cli_only_acp_flags_reach_the_session(monkeypatch, tmp_path):
    """--accept-hooks / --ignore-rules have no other route from the `hermes acp` parser to the owner."""
    for name in _ENV:
        monkeypatch.setenv(name, '')  # recorded, so cmd_acp's exports are undone after the test
    import acp_adapter.entry
    from hermes_cli.main_agent_cmds import cmd_acp
    monkeypatch.setattr(acp_adapter.entry, 'main', lambda argv: None)
    cmd_acp(SimpleNamespace(accept_hooks=True, ignore_rules=True))
    created = []
    await _agent(created).new_session(cwd=str(tmp_path))
    assert created[0].get('accept_hooks') is True and created[0].get('ignore_rules') is True
    assert 'yolo' not in created[0] and 'safe_mode' not in created[0]


@pytest.mark.asyncio
async def test_slow_editor_mcp_create_uses_a_separate_acp_rpc_budget(monkeypatch, tmp_path):
    """The observed 128 s build must outlive the 30 s default without exceeding the editor's 300 s."""
    from hermes_cli.gateway_client import DEFAULT_RPC_TIMEOUT

    for name in _ENV:
        monkeypatch.delenv(name, raising=False)
    created = []
    agent = _agent(created)
    normal_rpc = agent._gateway.rpc.side_effect
    budgets = []

    async def rpc(method, _timeout=None, **params):
        if method == 'session.create':
            budgets.append(_timeout)
        return await normal_rpc(method, **params)

    agent._gateway.rpc.side_effect = rpc
    editor_server = SimpleNamespace(model_dump=lambda **_: {
        'name': 'slow', 'command': 'npx', 'args': ['-y', 'test-mcp']})
    await agent.new_session(cwd=str(tmp_path), mcp_servers=[editor_server])

    assert len(budgets) == 1
    assert budgets[0] is not None and 120 < budgets[0] < 300
    assert budgets[0] > DEFAULT_RPC_TIMEOUT
    assert created[0]['editor']['mcp_servers'] == [editor_server.model_dump()]
    assert '_timeout' not in created[0]  # RPC-only deadline, never an on-wire session field
