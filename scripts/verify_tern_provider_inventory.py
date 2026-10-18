#!/usr/bin/env python3
"""Read-only parity probe for the active profile; emits provider/model ids, never credentials.

Run from the checkout with its runtime Python and HERMES_HOME pointing at the profile.
Feed stdout to HERMES_MODEL_PROVIDER_RECEIPT for the connected-SDK Vitest journey.
No session is persisted, prompt submitted, or configuration/credential changed by this probe.
Canonical inventory helpers may warm their ordinary catalog caches.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_output = sys.stdout  # server reserves stdout for JSON-RPC and redirects ordinary print to stderr

from hermes_cli.inventory import load_picker_context
from hermes_cli.model_switch import list_authenticated_providers
from hermes_constants import get_hermes_home
import tui_gateway.server as server

ctx = load_picker_context()
canonical = list_authenticated_providers(
    current_provider=ctx.current_provider, current_model=ctx.current_model,
    current_base_url=ctx.current_base_url, user_providers=ctx.user_providers,
    custom_providers=ctx.custom_providers, excluded_providers=ctx.excluded_providers,
    for_picker=True, non_blocking_catalogs=True, probe_custom_providers=False,
)
sid = 'read-only-provider-parity'
server._sessions[sid] = {'agent': None, 'profile_home': str(get_hermes_home()), 'session_key': sid}
try:
    response = server.handle_request({'id': 1, 'method': 'model.options', 'params': {
        'session_id': sid, 'explicit_only': False, 'include_unconfigured': True, 'safe_inventory': True}})
    if 'result' not in response:
        raise RuntimeError('model.options failed: ' + str(response.get('error', {}).get('code')))
    payload = response['result']
    fields = ('slug', 'name', 'models', 'authenticated', 'is_current', 'unavailable_models')
    safe_payload = {'model': payload['model'], 'provider': payload['provider'],
                    'providers': [{key: row[key] for key in fields if key in row} for row in payload['providers']]}
    expected = sorted({row['slug'] for row in canonical})
    actual = {row['slug'] for row in payload['providers']}
    missing = sorted(set(expected) - actual)
    print(json.dumps({'profile': get_hermes_home().name, 'canonical_providers': expected,
                      'missing': missing, 'options': safe_payload}, indent=2), file=_output)
    if missing:
        raise SystemExit(1)
finally:
    server._sessions.pop(sid, None)
