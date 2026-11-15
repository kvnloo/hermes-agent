"""Regression for NousResearch/hermes-agent#150397: routed local profile cwd survives session policy."""
import json
from dataclasses import asdict
from pathlib import Path

from gateway.session_policy import build_policy, policy_scope, restore_policy
from gateway.session_policy_refresh import refreshed_policy
from tools.terminal_scope import build_profile_terminal_scope, terminal_env


def test_routed_profile_local_cwd_beats_implicit_host_cwd_on_create_and_refresh(tmp_path, monkeypatch):
    home = tmp_path / '.hermes' / 'profiles' / 'luzio'
    home.mkdir(parents=True)
    workspace = tmp_path / 'Facturas_Luz'
    workspace.mkdir()
    daemon = tmp_path / 'gateway-launch'
    daemon.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    monkeypatch.setenv('HERMES_HOME', str(home))
    config = home / 'config.yaml'
    config.write_text(json.dumps({'terminal': {'backend': 'local', 'cwd': str(workspace)}}))
    params = {'source': 'gui', 'cwd': str(daemon), 'model': 'm'}

    policy = build_policy(params, {})
    with policy_scope(restore_policy(asdict(policy))):
        assert terminal_env('TERMINAL_CWD') == str(workspace)

    resumed, _, _ = refreshed_policy(policy, {}, build_profile_terminal_scope(home))
    with policy_scope(restore_policy(asdict(resumed))):
        assert terminal_env('TERMINAL_CWD') == str(workspace)

    chosen = build_policy({**params, 'cwd_explicit': True}, {})
    assert json.loads(chosen.terminal_json)['TERMINAL_CWD'] == str(daemon)

    config.write_text(json.dumps({'terminal': {'backend': 'local'}}))
    fallback = build_policy(params, {})
    assert json.loads(fallback.terminal_json)['TERMINAL_CWD'] == str(daemon)

    config.write_text(json.dumps({'terminal': {
        'backend': 'docker', 'cwd': str(workspace), 'docker_mount_cwd_to_workspace': True,
    }}))
    mounted = build_policy(params, {})
    assert json.loads(mounted.terminal_json)['TERMINAL_CWD'] == str(daemon)
