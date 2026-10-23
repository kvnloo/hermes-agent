"""Native-session import is a read-only catalog plus another viewer of the same gateway owner."""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from acp.schema import McpServerStdio

from acp_adapter.catalog import catalog_sessions
from acp_adapter.gateway_server import GatewayACPAgent
from acp_adapter.session import SessionManager
from hermes_state import SessionDB


def test_gateway_catalog_includes_human_surfaces_but_standalone_keeps_its_writer_boundary(tmp_path, caplog):
    path = tmp_path / 'state.db'
    sources = ('acp', 'cli', 'tui', 'gui', 'desktop', 'local', 'telegram', 'discord')
    with SessionDB(path) as db:
        for source in (*sources, 'oneshot', 'tool', 'api_server', 'subagent', 'fx-worker'):
            db.create_session(source, source=source, model='fixture', cwd=str(tmp_path),
                              session_key=f'{source}:fixture' if source in ('telegram', 'discord') else None)
            db.set_session_title(source, f'{source} conversation')
            db.append_message(source, 'user', f'{source} input')
        for sid in ('hidden', 'archived', 'empty'):
            db.create_session(sid, source='tui', cwd=str(tmp_path))
            if sid != 'empty':
                db.append_message(sid, 'user', sid)
        db.set_session_hidden('hidden', True)
        db.set_session_archived('archived', True)
        # A live session owned by the legacy in-process adapter must never gain a second writer.
        factory = Mock(side_effect=AssertionError('must not build another agent'))
        manager = SessionManager(db=db, agent_factory=factory)
        assert [row['session_id'] for row in manager.list_sessions()] == ['acp']
        for sid in set(sources) - {'acp'}:
            assert manager.get_session(sid) is None
        factory.assert_not_called()
    before = path.read_bytes()
    rows = catalog_sessions(path, str(tmp_path))
    assert {row['session_id'] for row in rows} == set(sources)
    assert 'use the gateway-backed ACP adapter' in caplog.text
    for row in rows:
        assert row['title'] == f"{row['session_id']} conversation"
        assert row['cwd'] == str(tmp_path)
        assert row['updated_at']
    assert not catalog_sessions(path, str(tmp_path / 'other'))
    assert path.read_bytes() == before


class _Bridge:
    def __init__(self, connection):
        self.connection, self.events, self.calls = connection, asyncio.Queue(), []

    async def rpc(self, method, _timeout=None, **params):
        from hermes_cli.gateway_client import rpc_error
        self.calls.append((method, params))
        reply = await self.connection.dispatch({'id': 1, 'method': method, 'params': params})
        if 'error' in reply:
            raise rpc_error(reply['error'])
        return reply['result']


class _Editor:
    def __init__(self):
        self.updates = []

    async def session_update(self, session_id, update, **kwargs):
        self.updates.append(update.model_dump(by_alias=True, exclude_none=True))


@pytest.mark.asyncio
@pytest.mark.parametrize('attach', ['load', 'resume'])
@pytest.mark.parametrize('source', ['tui', 'cli', 'gui'])
async def test_import_during_another_viewers_turn_preserves_owner_workspace_tools_and_fifo(
        tmp_path, monkeypatch, attach, source):
    from gateway import run
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    from gateway.session_authority import initialize_session_authority
    from gateway.session_controls import AuthorityConnection
    from gateway.session_local import create_local_session
    from hermes_state_runtime import admit_session_input, claim_session_input, list_session_admissions

    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    monkeypatch.setattr(run, '_load_gateway_config', lambda *args, **kwargs: {
        'platform_toolsets': {source: []}, 'auxiliary': {'title_generation': {'enabled': False}}})
    store = SessionStore(tmp_path / 'sessions', GatewayConfig())
    runner = SimpleNamespace(session_store=store, _session_db=store._db, adapters={}, _draining=False,
                             _cached_agent_for=lambda route: None)
    runner._adapter_for_source = lambda origin: runner.adapters.get(origin.platform)
    authority = await initialize_session_authority(runner, profile_id='fixture', instance_id='owner')
    agent = None
    try:
        original = AuthorityConnection(authority, object(), {'user_id': 'human', 'profile_id': 'fixture'})
        editor = AuthorityConnection(authority, object(), {'user_id': 'human', 'profile_id': 'fixture'})
        ref = create_local_session(authority, original.actor, {
            'request_id': 'native', 'source': source, 'cwd': str(tmp_path), 'model': 'fixture', 'toolsets': []})
        sid = ref.session_id
        db = authority.db
        db.append_message(sid, 'user', 'the native turn')
        db.append_message(sid, 'assistant', 'retained history')
        db.flush_token_counts()  # the picker is a different, read-only connection
        native = _Bridge(original)
        first = await native.rpc('session.resume', session_id=sid)
        admit_session_input(db, epoch=authority.epoch, principal_id=original.actor.subject,
                            session_id=sid, request_id='native-turn', payload={'text': 'still running'})
        claim_session_input(db, epoch=authority.epoch, session_id=sid)
        before = list_session_admissions(db, session_id=sid, pending_only=False)
        agent = GatewayACPAgent()
        agent._home, agent._gateway, agent._conn = Path(db.db_path).parent, _Bridge(editor), _Editor()
        listed = (await agent.list_sessions(cwd=str(tmp_path))).sessions
        assert [row.session_id for row in listed] == [sid]
        # T3's project and MCP selection are not the running conversation's launch policy.
        await getattr(agent, f'{attach}_session')(
            cwd=str(tmp_path / 'editor-project'), session_id=sid,
            mcp_servers=[McpServerStdio(name='editor-only', command='must-not-run', args=[], env=[])])
        snapshot = agent._snapshots[sid]
        assert snapshot['running'] is True
        assert snapshot['subscription_id'] != first['subscription_id']
        assert snapshot['info']['cwd'] == str(tmp_path)
        assert len(authority.sessions[sid].subscribers) == 2
        assert list_session_admissions(db, session_id=sid, pending_only=False) == before
        assert snapshot['execution_generation'] == before[0]['generation']
        assert any(update.get('content', {}).get('text') == 'retained history'
                   for update in agent._conn.updates)
        assert not agent._editor_mcp
        methods = [method for method, _ in agent._gateway.calls]
        assert not set(methods) & {'session.create', 'session.mutate', 'prompt.submit', 'session.interrupt'}
        assert all(set(params) == {'session_id'} for method, params in agent._gateway.calls
                   if method == 'session.resume')
        # Editor Stop without its own admission must not cancel the native viewer's turn.
        await agent.cancel(sid)
        assert list_session_admissions(db, session_id=sid, pending_only=False) == before
    finally:
        if agent is not None:
            for task in agent._background:
                task.cancel()
            await asyncio.gather(*agent._background, return_exceptions=True)
        store.close_all_db_handles()
