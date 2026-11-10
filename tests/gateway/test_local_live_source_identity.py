"""Live LOCAL restores compare the conversation, not a triggering message (#143537)."""
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_live_local_restore_ignores_message_id_but_rejects_foreign_identity(tmp_path, monkeypatch):
    from gateway import run
    from gateway.config import GatewayConfig, Platform
    from gateway.session import SessionStore
    from gateway.session_authority import initialize_session_authority
    from gateway.session_contract import SessionActor
    from gateway.session_local import create_local_session
    from gateway.session_local_recovery import restore_local_session
    from hermes_state_runtime import RuntimeStoreError

    monkeypatch.setattr(run, '_load_gateway_config', lambda: {'platform_toolsets': {'cli': []}})
    store = SessionStore(tmp_path / 'sessions', GatewayConfig())
    runner = SimpleNamespace(session_store=store, _session_db=store._db,
                             adapters={}, _draining=False)
    authority = await initialize_session_authority(runner, profile_id='fixture', instance_id='first')
    actor = SessionActor('owner', 'fixture', frozenset({'session:create', 'session:read'}), 'socket')
    params = {'request_id': 'first', 'source': 'gui', 'cwd': str(tmp_path),
              'model': 'frozen', 'toolsets': []}
    ref = create_local_session(authority, actor, params)
    live = authority.sessions[ref.session_id]
    assert runner.adapters[Platform.LOCAL].authorize_source(live.source)

    # Each turn stamps the same authorized source object with its own message ID.
    for message_id in ('turn-one', 'turn-two'):
        live.source.message_id = message_id
        assert restore_local_session(authority, ref.session_id) == ref

    # A different principal is still refused, even if only the live object was mutated.
    live.source.user_id = 'different-user'
    with pytest.raises(RuntimeStoreError, match='storage_unavailable'):
        restore_local_session(authority, ref.session_id)
