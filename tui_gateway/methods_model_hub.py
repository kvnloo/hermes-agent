"""Profile-owned model hub. Never exposes credentials or invents session auxiliary overrides."""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method
_profile_scoped = _registry.profile_scoped
_MAX_FALLBACKS = 8


def _hub_revision(raw):
    import hashlib
    import json
    return hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest()


def _hub_slots():
    from hermes_cli.web_server_config import _AUX_TASK_SLOTS, _plugin_aux_tasks
    return {**{slot: slot.replace('_', ' ').title() for slot in _AUX_TASK_SLOTS},
            **{entry['key']: str(entry.get('display_name') or entry['key']) for entry in _plugin_aux_tasks()}}


def _hub_route(value):
    if not isinstance(value, dict) or not value.get('model'):
        return None
    return {key: str(value.get(key) or '') for key in ('provider', 'model')}


def _hub_providers():
    from hermes_cli.inventory import build_model_options_payload, load_picker_context
    # Same canonical listing as /model, including pool-only, OAuth, key and user providers.
    # Project only safe fields: custom endpoints can embed passwords/query tokens.
    rows = build_model_options_payload(load_picker_context(), include_unconfigured=True)['providers']
    from tui_gateway.model_inventory import safe_provider_rows
    return safe_provider_rows(rows)


def _hub_writable():
    from hermes_cli.config import is_managed
    from hermes_cli.managed_scope import managed_config_keys
    roots = ('auxiliary', 'fallback_providers', 'fallback_model')
    return not is_managed() and not any(key == root or key.startswith(root + '.')
                                        for key in managed_config_keys() for root in roots)


@method('model.hub.get')
@_profile_scoped
def _hub_get(rid, params):
    from hermes_cli.config import _CONFIG_LOCK, require_readable_config_before_write
    from hermes_cli.fallback_config import get_fallback_chain
    try:
        with _sessions_lock:
            session = _settings_session(params)
            if session is None:
                raise LookupError('A live model management session is required.')
        slots, providers = _hub_slots(), _hub_providers()
        with _sessions_lock:
            _settings_session(params, session)
            with _CONFIG_LOCK:
                raw = require_readable_config_before_write()
                aux = raw.get('auxiliary') or {}
                roles = [{'id': slot, 'label': label, 'scope': 'profile',
                          'route': _hub_route(aux.get(slot))} for slot, label in slots.items()]
                return _ok(rid, {'profile': _settings_profile(), 'revision': _hub_revision(raw),
                                 'roles': roles, 'fallbacks': [_hub_route(row) for row in get_fallback_chain(raw)],
                                 'providers': providers, 'operations': {
                                     'role_scopes': ['profile'], 'fallback_scopes': ['profile'],
                                     'max_fallbacks': _MAX_FALLBACKS, 'native_login': False,
                                     'login_hint': 'Use Hermes model setup in a terminal; this inventory never accepts login secrets.',
                                     'writable': _hub_writable()}})
    except LookupError as exc:
        return _err(rid, 4001, str(exc))
    except Exception:
        return _err(rid, 5098, 'Model management could not be read. Check profile configuration and retry.')


def _hub_validate_route(route, providers):
    if not isinstance(route, dict) or set(route) != {'provider', 'model'}:
        raise ValueError('Choose a declared provider and model; credentials and endpoints are not accepted.')
    if not all(isinstance(route[key], str) and route[key] for key in ('provider', 'model')):
        raise ValueError('A provider and model are required.')
    provider = next((row for row in providers if row['slug'] == route['provider']), None)
    if (provider is None or provider.get('authenticated') is False or
            route['model'] not in provider.get('models', []) or
            route['model'] in provider.get('unavailable_models', []) or provider['slug'] == 'moa'):
        raise ValueError('This model is unavailable or its provider is locked. Refresh or configure the provider first.')
    return dict(route)


def _hub_clear_slot(slot):
    from hermes_cli.config import clear_model_endpoint_credentials
    slot = dict(slot or {})
    for key in ('provider', 'model', 'base_url', 'reasoning_effort'):
        slot.pop(key, None)
    clear_model_endpoint_credentials(slot)
    return slot


@method('model.hub.set')
@_profile_scoped
def _hub_set(rid, params):
    from hermes_cli.config import _CONFIG_LOCK, require_readable_config_before_write, save_config
    try:
        if params.get('scope') != 'profile' or type(params.get('confirmed', False)) is not bool:
            raise ValueError('Only explicit profile scope is supported for auxiliary roles and fallbacks.')
        with _sessions_lock:
            session = _settings_session(params)
            if session is None:
                raise LookupError('A live model management session is required.')
        slots, providers = _hub_slots(), _hub_providers()
        op = params.get('operation')
        if op not in ('role', 'fallbacks', 'reset_roles'):
            raise ValueError('Unsupported model management operation.')
        routes = []
        if op == 'role':
            if params.get('role') not in slots:
                raise ValueError('Unknown Hermes auxiliary role.')
            if params.get('route') is not None:
                routes = [_hub_validate_route(params['route'], providers)]
        if op == 'fallbacks':
            chain = params.get('fallbacks')
            if not isinstance(chain, list) or len(chain) > _MAX_FALLBACKS:
                raise ValueError(f'Fallback chains allow at most {_MAX_FALLBACKS} entries.')
            routes = [_hub_validate_route(row, providers) for row in chain]
            identities = [(row['provider'], row['model']) for row in routes]
            if len(identities) != len(set(identities)):
                raise ValueError('Repeated fallback routes create a cycle.')
        with _sessions_lock:
            _settings_session(params, session)
            with _CONFIG_LOCK:
                raw = require_readable_config_before_write()
                if params.get('profile') != _settings_profile() or params.get('revision') != _hub_revision(raw):
                    raise ValueError('Model settings changed. Reload before applying this change.')
                if not _hub_writable():
                    raise ValueError('Model management is administrator-managed and read-only.')
                primary = raw.get('model') or {}
                if op == 'fallbacks' and isinstance(primary, dict) and any(
                        row['provider'] == primary.get('provider') and row['model'] == primary.get('default')
                        for row in routes):
                    raise ValueError('The fallback chain cannot return to the primary model (cycle).')
                if not params.get('confirmed'):
                    return _ok(rid, {'confirm_required': True, 'confirm_message':
                                    'Confirm this exact profile-only model route change. It may use expensive models '
                                    'and change provider cost/data policy. Live session model pins stay unchanged.'})
                if op in ('role', 'reset_roles'):
                    aux = dict(raw.get('auxiliary') or {})
                    for slot in ([params['role']] if op == 'role' else slots):
                        aux[slot] = _hub_clear_slot(aux.get(slot))
                        if op == 'role' and routes:
                            aux[slot].update(routes[0])
                    raw['auxiliary'] = aux
                else:
                    from hermes_cli.fallback_config import get_fallback_chain
                    existing = get_fallback_chain(raw)
                    preserved = []
                    for route in routes:
                        matches = [row for row in existing if _hub_route(row) == route]
                        if len(matches) > 1:
                            raise ValueError('Ambiguous endpoint-specific fallback routes; manage this chain in Hermes setup.')
                        # Safe inventory omits private endpoint/key fields; a reorder must not erase them.
                        preserved.append(matches[0] if matches else route)
                    raw['fallback_providers'] = preserved
                    raw.pop('fallback_model', None)  # legacy entries must not resurrect on clear
                _settings_session(params, session)
                save_config(raw)
        return _ok(rid, {'confirm_required': False, 'confirm_message': ''})
    except LookupError as exc:
        return _err(rid, 4001, str(exc))
    except ValueError as exc:
        return _err(rid, 4002, str(exc))
    except Exception:
        return _err(rid, 5098, 'Model settings were not confirmed. Reload before retrying.')


def register(server):
    bind_module(globals(), server)
