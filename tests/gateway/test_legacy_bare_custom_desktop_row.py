"""An older Desktop chat whose row recorded only bare ``custom`` resumes on the profile's route.

Desktop builds before the session authority persisted the composer pick's resolved provider. For a
bare ``model.provider: custom`` profile whose entry lists no models, the row stored
``{'model': ..., 'provider': 'custom'}`` with no endpoint (``canonical_custom_identity`` had nothing
to heal it to). The old resume dropped that bare provider and ran the profile's route; adoption must
do the same, not freeze an endpointless ``custom`` route that resolves without the profile's key.
"""
import json

import pytest

URL = 'http://127.0.0.1:38263/v1'
PROFILE = {'provider': 'custom', 'base_url': URL, 'default': 'mock-model'}
LIST = {'model': PROFILE, 'custom_providers': [{'name': 'Mock', 'base_url': URL, 'key_env': 'OPENAI_API_KEY'}]}
DICT = {'model': PROFILE, 'providers': {'mock': {'name': 'Mock', 'api': URL, 'key_env': 'OPENAI_API_KEY'}}}


@pytest.mark.asyncio
@pytest.mark.parametrize('config', [LIST, DICT], ids=['custom_providers', 'providers'])
@pytest.mark.parametrize('model_config', [
    {'model': 'mock-model', 'provider': 'custom'},
    {'model': 'mock-model', 'provider': 'custom', 'api_mode': 'chat_completions'},
], ids=['provider-only', 'with-api-mode'])
async def test_a_bare_custom_desktop_row_resumes_on_the_profiles_route(monkeypatch, config, model_config):
    from gateway import run
    from gateway.session_local_migration import resolve_local_target
    from hermes_constants import get_hermes_home
    from tests.gateway.test_session_follow_profile_config import _owner, _route
    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run, '_hermes_home', home)
    monkeypatch.setenv('OPENAI_API_KEY', 'profile-key')  # the key lives in .env, loaded into the env
    (home / 'config.yaml').write_text(json.dumps(config))
    store, runner, authority, owner = _owner(home)
    runner._peek_session_state = lambda key: None
    try:
        authority.db.create_session('old-desktop', cwd=str(home), source='desktop', model='mock-model',
                                    model_config=model_config)
        authority._native_legacy_transports = {owner.actor.transport_id: owner.actor}
        live = authority.sessions[resolve_local_target(authority, owner.actor, 'old-desktop').session_id]
        assert _route(runner, live) == ('mock-model', URL, 'profile-key')
    finally:
        await owner.close()
        store.close_all_db_handles()

OLD_URL = 'http://127.0.0.1:38262/v1'


@pytest.mark.asyncio
async def test_a_billed_bare_custom_desktop_row_follows_changed_profile(monkeypatch):
    """A prior turn's billing endpoint must not turn a Desktop billing label into a route pick."""
    from gateway import run
    from gateway.session_local_migration import resolve_local_target
    from hermes_constants import get_hermes_home
    from tests.gateway.test_session_follow_profile_config import _owner, _route

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(run, '_hermes_home', home)
    monkeypatch.setenv('OPENAI_API_KEY', 'profile-key')
    (home / 'config.yaml').write_text(json.dumps(LIST))  # the profile now serves URL, not OLD_URL
    store, runner, authority, owner = _owner(home)
    runner._peek_session_state = lambda key: None
    try:
        authority.db.create_session('old-desktop', cwd=str(home), source='desktop', model='mock-model',
                                    model_config={'model': 'mock-model', 'provider': 'custom'})
        # Real persisted accounting route from the old endpoint, not a user-selected model route.
        authority.db.update_session_billing_route('old-desktop', provider='custom', base_url=OLD_URL)
        row = authority.db.get_session('old-desktop')
        assert row['billing_base_url'] == OLD_URL
        authority._native_legacy_transports = {owner.actor.transport_id: owner.actor}
        live = authority.sessions[resolve_local_target(authority, owner.actor, 'old-desktop').session_id]
        assert _route(runner, live) == ('mock-model', URL, 'profile-key')
    finally:
        await owner.close()
        store.close_all_db_handles()
