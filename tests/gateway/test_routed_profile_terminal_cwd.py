"""Regression for NousResearch/hermes-agent#150397: routed local profile cwd survives session policy."""
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from gateway.session_policy import build_policy, policy_scope, restore_policy
from gateway.session_policy_refresh import refreshed_policy
from hermes_state_runtime import RuntimeStoreError
from tools.terminal_scope import build_profile_terminal_scope, terminal_env


@pytest.fixture
def routed_profile(tmp_path, monkeypatch):
    home = tmp_path / '.hermes' / 'profiles' / 'luzio'
    home.mkdir(parents=True)
    workspace = tmp_path / 'Facturas_Luz'
    workspace.mkdir()
    daemon = tmp_path / 'gateway-launch'
    daemon.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setenv('HERMES_HOME', str(home))
    (home / 'config.yaml').write_text(json.dumps({'terminal': {'backend': 'local', 'cwd': str(workspace)}}))
    return home, workspace, daemon


def assert_workspace(policy, workspace):
    assert policy.cwd == str(workspace)
    with policy_scope(restore_policy(asdict(policy))):
        assert terminal_env('TERMINAL_CWD') == str(workspace)
        from tools.terminal_tool import _get_env_config
        config = _get_env_config()
        assert (config.get('host_cwd') or config['cwd']) == str(workspace)


@pytest.mark.parametrize('launch', [{}, {'cwd_explicit': False}])
def test_routed_profile_local_cwd_beats_implicit_host_cwd_on_create_and_refresh(routed_profile, launch):
    home, workspace, daemon = routed_profile
    params = {'source': 'gui', 'cwd': str(daemon), 'model': 'm', **launch}
    policy = build_policy(params, {})
    assert_workspace(policy, workspace)
    assert json.loads(policy.request_json)['cwd'] == str(daemon)

    resumed, _, _ = refreshed_policy(policy, {}, build_profile_terminal_scope(home))
    assert_workspace(resumed, workspace)

    moved = workspace.parent / 'updated-workspace'
    moved.mkdir()
    (home / 'config.yaml').write_text(json.dumps({'terminal': {'backend': 'local', 'cwd': str(moved)}}))
    resumed, _, _ = refreshed_policy(policy, {}, build_profile_terminal_scope(home))
    assert_workspace(resumed, moved)
    assert json.loads(resumed.request_json) == json.loads(policy.request_json)
    # Restoring a frozen receipt must not re-read today's profile config.
    assert_workspace(policy, workspace)


@pytest.mark.parametrize('picked', [(), ('workspace',)])
def test_explicit_session_workspace_wins_on_create_and_refresh(routed_profile, picked):
    home, _, daemon = routed_profile
    policy = build_policy({'source': 'gui', 'cwd': str(daemon), 'model': 'm', 'cwd_explicit': True}, {})
    assert_workspace(policy, daemon)
    if picked:
        from dataclasses import replace
        policy = replace(policy, request_json=json.dumps({'source': 'gui', 'cwd': str(daemon), 'model': 'm'}))
    resumed, _, _ = refreshed_policy(policy, {}, build_profile_terminal_scope(home), picked=picked)
    assert_workspace(resumed, daemon)


@pytest.mark.parametrize('terminal', [
    {'backend': 'local'},
    {'backend': 'local', 'cwd': '.'},
    {'backend': 'local', 'cwd': 'auto'},
    {'backend': 'local', 'cwd': 'cwd'},
    {'backend': 'local', 'cwd': 'missing-directory'},
    {'backend': 'docker', 'docker_mount_cwd_to_workspace': True},
])
def test_unset_profile_and_mounted_docker_fall_back_to_launch_cwd(routed_profile, terminal):
    home, workspace, daemon = routed_profile
    if terminal['backend'] == 'docker':
        terminal = {**terminal, 'cwd': str(workspace)}
    (home / 'config.yaml').write_text(json.dumps({'terminal': terminal}))
    policy = build_policy({'source': 'gui', 'cwd': str(daemon), 'model': 'm'}, {})
    assert_workspace(policy, daemon)
    resumed, _, _ = refreshed_policy(policy, {}, build_profile_terminal_scope(home))
    assert_workspace(resumed, daemon)


def test_preserving_profile_cwd_does_not_relax_receipt_validation(routed_profile):
    home, _, daemon = routed_profile
    policy = build_policy({'source': 'gui', 'cwd': str(daemon), 'model': 'm'}, {})
    corrupted = {**asdict(policy), 'cwd': str(home)}
    with pytest.raises(RuntimeStoreError, match='storage_unavailable'):
        restore_policy(corrupted)


@pytest.mark.asyncio
async def test_routed_profile_cwd_survives_authority_recovery_and_resume(routed_profile, monkeypatch):
    from gateway import run
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    from gateway.session_authority import initialize_session_authority
    from gateway.session_controls import AuthorityConnection
    from hermes_state_local import local_receipt
    from tests.gateway.test_session_resume_config_refresh import _call, _policy, _runner

    home, workspace, daemon = routed_profile
    monkeypatch.setattr(run, '_hermes_home', home)
    store = SessionStore(home / 'sessions', GatewayConfig())
    owner = viewer = None
    try:
        authority = await initialize_session_authority(_runner(store), profile_id=str(home), instance_id='first')
        owner = AuthorityConnection(authority, object(), {'user_id': 'human'})
        params = {'request_id': 'profile-cwd', 'source': 'gui', 'cwd': str(daemon), 'model': 'm'}
        created = await _call(owner, 'session.create', **params)
        sid = created['session_id']
        assert_workspace(restore_policy(local_receipt(store._db, sid)['policy']), workspace)
        await owner.close()
        owner = None
        generation = store._db.get_session(sid)['runtime_generation']
        moved = workspace.parent / 'resumed-workspace'
        moved.mkdir()
        (home / 'config.yaml').write_text(json.dumps({'terminal': {'backend': 'local', 'cwd': str(moved)}}))
        cold = await initialize_session_authority(_runner(store), profile_id=str(home), instance_id='recovered')
        viewer = AuthorityConnection(cold, object(), {'user_id': 'human'})
        resumed = await _call(viewer, 'session.resume', session_id=sid)
        assert resumed['execution_generation'] == generation + 1
        assert_workspace(_policy(cold, sid), moved)
        receipt = local_receipt(store._db, sid)
        assert_workspace(restore_policy(receipt['policy']), moved)
        assert json.loads(receipt['policy']['request_json'])['cwd'] == str(daemon)
        assert (await _call(viewer, 'session.create', **params))['session_id'] == sid
        assert (await _call(viewer, 'session.resume', session_id=sid))['execution_generation'] == generation + 1
    finally:
        for connection in (owner, viewer):
            if connection is not None:
                await connection.close()
        store.close_all_db_handles()
