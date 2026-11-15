"""Regression for NousResearch/hermes-agent#150409: editor MCP needs the optional ACP extra."""
import builtins

import pytest

from gateway.session_local_mcp import private_mutation_payload, validate_servers
from hermes_state_runtime import RuntimeStoreError


def _make_acp_import_fail(monkeypatch, missing):
    original_import = builtins.__import__

    def import_without_acp(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'acp.schema':
            raise ModuleNotFoundError(f"No module named '{missing}'", name=missing)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', import_without_acp)


@pytest.mark.parametrize('missing', ['acp', 'acp.schema'])
@pytest.mark.parametrize('operation', ['editor_mcp', 'branch'])
def test_missing_acp_extra_is_actionable_in_editor_mcp_mutation(monkeypatch, missing, operation):
    _make_acp_import_fail(monkeypatch, missing)
    with pytest.raises(RuntimeStoreError) as caught:
        private_mutation_payload(operation, {'mcp_servers': [
            {'type': 'stdio', 'name': 'editor', 'command': 'python', 'args': []},
        ]})
    refusal = caught.value
    assert refusal.reason == 'acp_extra_missing'
    assert refusal.field == 'editor.mcp_servers'
    assert "'[acp]'" in refusal.detail
    assert str(refusal) == 'acp_extra_missing'


@pytest.mark.parametrize('missing', ['other_optional_dependency', 'acp.internal_dependency'])
def test_unrelated_import_failure_is_not_misreported_as_missing_acp(monkeypatch, missing):
    _make_acp_import_fail(monkeypatch, missing)
    with pytest.raises(ModuleNotFoundError) as caught:
        validate_servers([{'type': 'stdio', 'name': 'editor', 'command': 'python', 'args': []}])
    assert caught.value.name == missing


@pytest.mark.asyncio
@pytest.mark.parametrize('missing', ['acp', 'acp.schema'])
async def test_missing_acp_extra_reaches_session_create_client(tmp_path, monkeypatch, missing):
    """Exercise the real create handler and refusal serialization, without a running service."""
    from types import SimpleNamespace

    from gateway.session_authority import SessionAuthority
    from gateway.session_controls import AuthorityConnection
    from hermes_state import SessionDB
    from hermes_state_runtime import begin_runtime_epoch

    _make_acp_import_fail(monkeypatch, missing)
    with SessionDB(db_path=tmp_path / 'state.db') as db:
        epoch = begin_runtime_epoch(db, instance_id='test')
        runner = SimpleNamespace(_user_config={'platform_toolsets': {'cli': ['terminal']}})
        authority = SessionAuthority(runner, profile_id='test', instance_id='test', db=db, epoch=epoch)
        connection = AuthorityConnection(authority, object(), {'user_id': 'human'})
        reply = await connection.dispatch({'id': 7, 'method': 'session.create', 'params': {
            'source': 'acp', 'cwd': str(tmp_path), 'editor': {'mcp_servers': [
                {'type': 'stdio', 'name': 'editor', 'command': 'python', 'args': []},
            ]},
        }})
    assert reply['id'] == 7
    assert reply['error']['message'] == 'acp_extra_missing'
    data = reply['error']['data']
    assert data['reason'] == 'acp_extra_missing'
    assert data['field'] == 'editor.mcp_servers'
    assert "'[acp]'" in data['detail']
    assert 'agent-client-protocol' in data['detail']
