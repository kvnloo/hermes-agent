"""Revision-bound model hub consumer tests; only isolated profiles are mutated."""
import copy
import json

import pytest

import tui_gateway.server as server
from tests.tui_gateway.test_settings_contract import homes, result, rpc, saved, seed  # noqa: F401


@pytest.fixture(autouse=True)
def inventory(monkeypatch):
    rows = [
        {'slug': slug, 'name': slug, 'authenticated': True, 'models': ['one', 'two']}
        for slug in ('pool', 'oauth', 'key', 'custom:lab')
    ] + [{'slug': 'locked', 'name': 'Locked', 'authenticated': False, 'models': ['one']},
         {'slug': 'limited', 'name': 'Limited', 'authenticated': True, 'models': ['one'],
          'unavailable_models': ['one']}]
    monkeypatch.setattr(server, '_hub_providers', lambda: copy.deepcopy(rows))
    return rows


def read(sid='worker'):
    return result(rpc('model.hub.get', session_id=sid))


def edit(snapshot, **extra):
    return rpc('model.hub.set', session_id='worker', profile=snapshot['profile'],
               revision=snapshot['revision'], scope='profile', **extra)


def test_supported_metadata_roles_and_secret_free_inventory(homes, monkeypatch):
    import hermes_cli.inventory as inv
    # Test the real projection, not only a pre-sanitized fixture.
    from tui_gateway.methods_model_hub import _hub_providers
    calls = []
    def build(ctx, **kwargs):
        calls.append(kwargs)
        return {'providers': [{'slug': 'custom:lab', 'name': 'Lab', 'models': ['one'],
                               'authenticated': True, 'api_key': 'secret-key',
                               'api_url': 'https://user:secret@example.test/v1?token=secret',
                               'warning': 'secret-warning'}]}
    monkeypatch.setattr(inv, 'build_model_options_payload', build)
    projected = _hub_providers()
    assert calls == [{'include_unconfigured': True}]
    assert 'secret' not in json.dumps(projected)
    assert projected[0]['slug'] == 'custom:lab'
    options = result(rpc('model.options', session_id='worker', safe_inventory=True))
    assert [row['slug'] for row in options['providers']] == ['custom:lab']
    assert 'secret' not in json.dumps(options)
    snapshot = read()
    assert snapshot['operations']['role_scopes'] == ['profile']
    assert snapshot['operations']['native_login'] is False
    assert snapshot['operations']['max_fallbacks'] == 8
    assert 'vision' in [row['id'] for row in snapshot['roles']]
    assert {row['slug'] for row in snapshot['providers']} >= {'pool', 'oauth', 'key', 'custom:lab', 'locked'}


def test_model_inventory_reports_pending_intent_without_raw_switch_or_secret(homes, monkeypatch):
    import hermes_cli.inventory as inv
    monkeypatch.setattr(inv, 'build_model_options_payload', lambda *a, **kw: {
        'providers': [], 'model': 'active', 'provider': 'pool'})
    server._sessions['worker']['pending_model_switch'] = {
        'raw': 'secret-raw-switch', 'display_model': 'next', 'display_provider': 'oauth'}
    response = result(rpc('model.options', session_id='worker', safe_inventory=True))
    assert response['model'] == 'active'
    assert response['pending_model'] == 'next'
    assert response['pending_provider'] == 'oauth'
    assert 'secret' not in json.dumps(response)
    server._sessions['worker'].pop('pending_model_switch')
    assert 'pending_model' not in result(rpc('model.options', session_id='worker', safe_inventory=True))


def test_set_clear_role_confirmation_canonical_readback_and_profile_isolation(homes):
    launch, worker = homes
    before_launch = (launch / 'config.yaml').read_bytes()
    before_session = copy.deepcopy(server._sessions['worker'])
    seed(worker, {'model': {'default': 'worker-model'}, 'auxiliary': {
        'vision': {'provider': 'old', 'model': 'old', 'api_key': 'old-secret',
                   'base_url': 'https://old.test', 'timeout': 12}}, 'unrelated': {'keep': True}})
    first = read()
    intent = dict(operation='role', role='vision', route={'provider': 'custom:lab', 'model': 'one'})
    before = (worker / 'config.yaml').read_bytes()
    assert result(edit(first, **intent))['confirm_required'] is True
    assert (worker / 'config.yaml').read_bytes() == before
    assert result(edit(first, **intent, confirmed=True))['confirm_required'] is False
    slot = saved(worker)['auxiliary']['vision']
    assert slot == {'provider': 'custom:lab', 'model': 'one', 'timeout': 12}
    next_read = read()
    assert next(row for row in next_read['roles'] if row['id'] == 'vision')['route'] == intent['route']
    assert next_read['revision'] != first['revision']
    assert 'error' in edit(first, **intent, confirmed=True)
    result(edit(next_read, operation='role', role='vision', route=None, confirmed=True))
    assert saved(worker)['auxiliary']['vision'] == {'timeout': 12}
    assert saved(worker)['unrelated'] == {'keep': True}
    assert (launch / 'config.yaml').read_bytes() == before_launch
    assert server._sessions['worker'] == before_session


@pytest.mark.parametrize('route', [
    {'provider': 'locked', 'model': 'one'}, {'provider': 'limited', 'model': 'one'},
    {'provider': 'pool', 'model': 'missing'}, {'provider': 'missing', 'model': 'one'},
    {'provider': 'pool', 'model': 'one', 'api_key': 'not-accepted'},
])
def test_unavailable_locked_and_credential_payloads_cannot_write(homes, route):
    worker = homes[1]
    snapshot = read()
    before = (worker / 'config.yaml').read_bytes()
    assert 'error' in edit(snapshot, operation='role', role='vision', route=route, confirmed=True)
    assert (worker / 'config.yaml').read_bytes() == before


def test_bounded_ordered_fallbacks_and_scoped_resets_do_not_resurrect_legacy(homes):
    worker = homes[1]
    seed(worker, {'model': {'provider': 'pool', 'default': 'one'},
                  'fallback_model': {'provider': 'key', 'model': 'two'},
                  'auxiliary': {'vision': {'provider': 'key', 'model': 'one'}}})
    chain = [{'provider': 'oauth', 'model': 'one'}, {'provider': 'custom:lab', 'model': 'two'}]
    result(edit(read(), operation='fallbacks', fallbacks=chain, confirmed=True))
    assert read()['fallbacks'] == chain
    assert 'fallback_model' not in saved(worker)
    result(edit(read(), operation='reset_roles', confirmed=True))
    assert read()['fallbacks'] == chain
    assert next(row for row in read()['roles'] if row['id'] == 'vision')['route'] is None
    result(edit(read(), operation='fallbacks', fallbacks=[], confirmed=True))
    assert read()['fallbacks'] == []
    assert saved(worker)['model'] == {'provider': 'pool', 'default': 'one'}


@pytest.mark.parametrize('chain', [
    [{'provider': 'pool', 'model': 'one'}] * 9,
    [{'provider': 'oauth', 'model': 'one'}] * 2,
    [{'provider': 'pool', 'model': 'one'}],
])
def test_fallback_bound_duplicate_and_primary_cycles_rejected(homes, chain):
    worker = homes[1]
    seed(worker, {'model': {'provider': 'pool', 'default': 'one'}})
    before = (worker / 'config.yaml').read_bytes()
    assert 'error' in edit(read(), operation='fallbacks', fallbacks=chain, confirmed=True)
    assert (worker / 'config.yaml').read_bytes() == before


def test_stale_profile_session_scope_and_managed_settings_refused(homes, monkeypatch):
    snapshot = read()
    intent = dict(operation='role', role='vision', route={'provider': 'key', 'model': 'one'}, confirmed=True)
    response = rpc('model.hub.set', session_id='worker', profile='worker', revision=snapshot['revision'],
                   scope='session', **intent)
    assert 'error' in response
    monkeypatch.setattr(server, '_hub_writable', lambda: False)
    assert read()['operations']['writable'] is False
    assert 'error' in edit(snapshot, **intent)
    monkeypatch.setattr(server, '_hub_writable', lambda: True)
    server._sessions['worker']['_finalized'] = True
    assert 'error' in edit(snapshot, **intent)
    assert 'error' in rpc('model.hub.get', session_id='worker')


def test_fallback_reorder_preserves_hidden_route_credentials_and_endpoints(homes):
    worker = homes[1]
    original = {'provider': 'custom:lab', 'model': 'one', 'base_url': 'https://private.example/v1',
                'api_key': '${TEST_ROUTE_KEY}', 'api_mode': 'chat_completions'}
    seed(worker, {'fallback_providers': [original]})
    snapshot = read()
    assert snapshot['fallbacks'] == [{'provider': 'custom:lab', 'model': 'one'}]
    assert 'private.example' not in json.dumps(snapshot)
    assert 'TEST_ROUTE_KEY' not in json.dumps(snapshot)
    result(edit(snapshot, operation='fallbacks', fallbacks=[{'provider': 'key', 'model': 'two'},
                  {'provider': 'custom:lab', 'model': 'one'}], confirmed=True))
    assert saved(worker)['fallback_providers'][1] == original


def test_session_replaced_during_inventory_cannot_write(homes, monkeypatch):
    snapshot = read()
    worker = homes[1]
    before = (worker / 'config.yaml').read_bytes()
    original = server._hub_providers
    def replace():
        server._sessions['worker'] = dict(server._sessions['worker'])
        return original()
    monkeypatch.setattr(server, '_hub_providers', replace)
    assert 'error' in edit(snapshot, operation='reset_roles', confirmed=True)
    assert (worker / 'config.yaml').read_bytes() == before
