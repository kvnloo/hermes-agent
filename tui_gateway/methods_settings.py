"""Schema-driven profile settings over the existing gateway, with one config authority.

Bodies are rebound onto server.py's globals by method_ctx. Settings never mutate live
session pins. Credential-shaped leaves use the canonical config classifier and null
preservation, not display previews with write authority.
"""

from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method
_profile_scoped = _registry.profile_scoped


def _settings_session(params, expected=None):
    from hermes_constants import named_profile_is_deleted
    sid = params.get("session_id")
    if not sid:
        return None
    session = _sessions.get(sid)
    if session is None or session.get("_finalized") or (expected is not None and session is not expected):
        raise LookupError("The settings session is no longer live. Open Settings again.")
    runtime_record = _current_runtime_session_record.get()
    if runtime_record is not None and session is not runtime_record:
        raise LookupError("The settings session has changed. Open Settings again.")
    if current_transport() is not None and not _session_transport_contains(session, current_transport()):
        raise LookupError("The settings session is not attached to this client.")
    home = Path(session.get("profile_home") or _launch_home()).resolve()
    if home != get_hermes_home().resolve():
        raise LookupError("The settings profile does not own this session. Open Settings again.")
    if not home.is_dir() or named_profile_is_deleted(home):
        raise LookupError("The settings profile is no longer available. Open Settings again.")
    return session


def _settings_profile():
    return profile_name_for_home(str(get_hermes_home())) or _current_profile_name()


def _settings_leaf(config, key, fallback=None):
    from hermes_cli.config import cfg_get
    return cfg_get(config, *key.split("."), default=fallback)


def _settings_secret_key(key):
    from hermes_cli.config import _is_secret_config_key
    # Password hashes authenticate just like plaintext, but the CLI classifier predates this field.
    return _is_secret_config_key(key) or key.rsplit(".", 1)[-1].lower() == "password_hash"


def _settings_private_value(value, key=""):
    if _settings_secret_key(key):
        return None, True
    if isinstance(value, dict):
        result, sensitive = {}, False
        for name, item in value.items():
            result[name], hidden = _settings_private_value(item, str(name))
            sensitive = sensitive or hidden
        return result, sensitive
    if isinstance(value, list):
        rows = [_settings_private_value(item) for item in value]
        return [item for item, _ in rows], any(hidden for _, hidden in rows)
    return value, False


def _settings_templates(effective, raw):
    """Show raw environment references, not their possibly-secret expanded values."""
    from hermes_cli.config import _ENV_REF_RE
    if isinstance(raw, str) and _ENV_REF_RE.search(raw):
        return raw
    if isinstance(effective, dict) and isinstance(raw, dict):
        return {key: _settings_templates(value, raw.get(key)) for key, value in effective.items()}
    if isinstance(effective, list) and isinstance(raw, list):
        return [_settings_templates(value, raw[index] if index < len(raw) else None)
                for index, value in enumerate(effective)]
    return effective


def _settings_raw_layers(raw, effective):
    from hermes_cli.config import _deep_merge, _normalize_root_model_keys
    from hermes_cli.managed_scope import load_managed_config
    raw = _normalize_root_model_keys(raw)
    managed = _normalize_root_model_keys(load_managed_config())
    if isinstance(managed.get("model"), str):
        managed = {**managed, "model": {"default": managed["model"]}}
    if isinstance(raw.get("model"), str) and isinstance(effective.get("model"), dict):
        raw = {**raw, "model": {"default": raw["model"]}}
    return _deep_merge(raw, managed)


def _settings_fields(raw, schemas):
    from hermes_cli.config import DEFAULT_CONFIG, _ENV_REF_RE, load_config
    from hermes_cli.web_server_config import CONFIG_SCHEMA, _normalize_config_for_web
    from hermes_constants import VALID_REASONING_EFFORTS, parse_reasoning_effort
    effective = load_config()
    expanded = _normalize_config_for_web(effective)
    cfg = _normalize_config_for_web(_settings_templates(effective, _settings_raw_layers(raw, effective)))
    defaults = _normalize_config_for_web(DEFAULT_CONFIG)
    fields = {}
    for key, schema in schemas.items():
        value, sensitive = _settings_private_value(_settings_leaf(cfg, key), key)
        default, default_sensitive = _settings_private_value(_settings_leaf(defaults, key), key)
        field = {name: schema[name] for name in ("type", "description", "category", "options", "nullable")
                 if name in schema}
        if "options" in field:
            options = list(field["options"])
            source_value = _settings_leaf(cfg, key)
            if isinstance(source_value, str) and _ENV_REF_RE.search(source_value):
                expanded_value = str(_settings_leaf(expanded, key)).strip().casefold()
                literal_options = CONFIG_SCHEMA[key].get("options", ())
                options = [source_value if option not in literal_options and option.strip().casefold() == expanded_value
                           else option for option in options]
                if source_value not in options:
                    options.append(source_value)
            field["options"] = options
        if schema.get("clearable") and "options" in field:
            field["options"] = list(dict.fromkeys(["", *field["options"]]))
        if key == "agent.reasoning_effort" and not (isinstance(value, str) and _ENV_REF_RE.search(value)):
            parsed = parse_reasoning_effort(value)
            if isinstance(value, dict) and (
                    value.keys() - {"enabled", "effort"} or parsed is None
                    or (parsed.get("enabled") is not False and parsed.get("effort") not in VALID_REASONING_EFFORTS)):
                # Bespoke provider tiers require their supported dict form, not an invalid bare string.
                field["type"] = "object"
                field.pop("options", None)
            elif parsed is not None:
                value = "none" if parsed.get("enabled") is False else parsed["effort"]
            elif value is True or value == "":
                value = None
        field.update(value=value, default=default, sensitive=sensitive or default_sensitive)
        fields[key] = field
    return fields


def _settings_json(value):
    import math
    if value is None or isinstance(value, (str, bool)):
        return True
    if type(value) is int:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_settings_json(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _settings_json(item) for key, item in value.items())
    return False


def _settings_validate(key, value, field):
    if not _settings_json(value):
        raise ValueError(f"{key} must contain finite JSON values.")
    if value is None and (field.get("nullable") or _settings_secret_key(key)):
        return
    kind = field["type"]
    valid = {"boolean": type(value) is bool,
             "number": type(value) in (int, float),
             "string": isinstance(value, str), "select": isinstance(value, str),
             "list": isinstance(value, list), "object": isinstance(value, dict)}.get(kind, False)
    if not valid:
        raise ValueError(f"{key} requires a {kind} value.")
    options = field.get("options")
    if options is not None and value not in options and not (value == "" and field.get("clearable")):
        raise ValueError(f"{key} requires one of its declared options.")
    if key == "model_context_length" and (type(value) is not int or value < 0):
        raise ValueError("model_context_length requires a non-negative integer (0 means automatic).")
    if key == "model" and not value.strip():
        raise ValueError("model requires a non-empty model name.")


def _settings_row_identity(row):
    if not isinstance(row, dict):
        return None
    for name in ("name", "id"):
        if isinstance(row.get(name), str) and row[name]:
            return (name, row[name])
    if row.get("provider") or row.get("model"):
        return ("route", row.get("provider"), row.get("model"), row.get("base_url"))
    return None


def _settings_preserve_credentials(value, old, key=""):
    from hermes_cli.web_routers._common import is_redacted_credential_preview
    if _settings_secret_key(key):
        if value is None:
            return old
        if is_redacted_credential_preview(value):
            raise ValueError("A redacted credential preview cannot replace a credential.")
        return value
    if isinstance(value, dict):
        return _settings_preserve_mapping_credentials(value, old)
    if isinstance(value, list):
        return _settings_preserve_list_credentials(value, old)
    return value


def _settings_preserve_mapping_credentials(value, old):
    old = old if isinstance(old, dict) else {}
    result = {name: _settings_preserve_credentials(item, old.get(name), str(name))
              for name, item in value.items()}
    for name, item in value.items():
        if _settings_secret_key(str(name)) and item is None and name not in old:
            result.pop(name, None)
    for name, item in old.items():
        if name not in result and _settings_private_value(item, str(name))[1]:
            result[name] = item
    return result


def _settings_previous_credential_row(item, old):
    identity = _settings_row_identity(item)
    if identity is None:
        if _settings_private_value(item)[1]:
            raise ValueError("Credential-bearing rows require a unique name or route.")
        return None
    matches = [row for row in old if _settings_row_identity(row) == identity]
    if len(matches) > 1 and any(_settings_private_value(row)[1] for row in matches):
        raise ValueError("Credential-bearing rows require unique names or routes.")
    return matches[0] if matches else None


def _settings_preserve_list_credentials(value, old):
    old = old if isinstance(old, list) else []
    result = [_settings_preserve_credentials(item, _settings_previous_credential_row(item, old))
              for item in value]
    seen = []
    for row in result:
        identity = _settings_row_identity(row)
        sensitive = _settings_private_value(row)[1]
        if identity is not None and any(previous == identity and (sensitive or hidden)
                                        for previous, hidden in seen):
            raise ValueError("Credential-bearing rows require unique names or routes.")
        seen.append((identity, sensitive))
    for row in old:
        identity = _settings_row_identity(row)
        if _settings_private_value(row)[1] and (
                identity is None or not any(_settings_row_identity(item) == identity for item in value)):
            result.append(row)
    return result


_SETTINGS_RISK_ROOTS = frozenset({
    "approvals", "auth", "security", "privacy", "telemetry", "monitoring", "secrets", "vault",
    "proxy", "terminal", "providers", "fallback_providers", "hooks", "hooks_auto_accept",
    "command_allowlist", "computer_use", "lsp", "plugins", "gateway", "model",
    "quick_commands", "skills", "browser",
})
_SETTINGS_CONSENT_KEYS = frozenset({"telemetry.shared_metrics.enabled", "telemetry.shared_metrics.send"})


def _settings_write_paths(key):
    if key == "model_context_length":
        return (key, "model.context_length")
    if key in _SETTINGS_CONSENT_KEYS:
        return tuple(_SETTINGS_CONSENT_KEYS)
    return (key,)


def _settings_confirmation(key, value, field, profile):
    import json
    safe, hidden = _settings_private_value(value, key)
    route_change = key.endswith((".provider", ".model", ".base_url", ".api_mode"))
    if key not in _SETTINGS_CONSENT_KEYS and key.split(".", 1)[0] not in _SETTINGS_RISK_ROOTS and not (field.get("sensitive") or hidden or route_change):
        return ""
    target = "a new credential (hidden)" if _settings_secret_key(key) else json.dumps(safe, ensure_ascii=False)
    message = f"Set profile '{profile}' default {key} to {target}? Live session overrides stay unchanged."
    if key in _SETTINGS_CONSENT_KEYS:
        from hermes_cli.observability.shared_metrics_consent import _OFFER_DESCRIPTION
        message += "\n" + _OFFER_DESCRIPTION
        if key.endswith(".send") and value is True:
            message += "\nThis also enables local collection."
        elif key.endswith(".enabled") and value is False:
            message += "\nThis also withdraws permission to send."
    elif key == "model":
        message += "\nThe default model can change provider cost and data policy."
    else:
        message += "\nThis can change execution, access, credentials, privacy or consent policy."
    return message


def _settings_patch(key, value):
    result = value
    for part in reversed(key.split(".")):
        result = {part: result}
    return result


def _settings_save(key, value, raw):
    from hermes_cli.config import DEFAULT_CONFIG, _deep_merge, _strip_dotted_keys, save_config
    from hermes_cli.web_server_config import _denormalize_config_from_web
    if key in _SETTINGS_CONSENT_KEYS:
        from hermes_cli.observability.shared_metrics_consent import consent_state, save_consent
        state = consent_state(raw)
        enabled = value if key.endswith(".enabled") else state["enabled"] or value
        send = value if key.endswith(".send") else state["send"] and enabled
        save_consent(enabled, send)
        if not enabled:
            from hermes_cli.observability.shared_metrics_desktop import purge_onboarding_latches
            purge_onboarding_latches()
        return
    patch = _denormalize_config_from_web(_settings_patch(key, value))
    missing = object()
    if key == "model_context_length" and value == 0:
        # The canonical sparse writer intentionally does not delete omitted keys. Only this
        # explicit virtual-field removal uses a full RAW snapshot under the same config lock.
        merged = _deep_merge(raw, patch)
        if isinstance(merged.get("model"), dict):
            merged["model"].pop("context_length", None)
        save_config(merged)
    elif value is None and _settings_leaf(DEFAULT_CONFIG, key, missing) is missing:
        # Optional runtime fields inherit only when absent, not when pinned to YAML null.
        _strip_dotted_keys(raw, {key})
        save_config(raw)
    elif isinstance(value, dict):
        # A structured field is one declared leaf. An explicit {} must revert that leaf,
        # not deep-merge yesterday's entries back into it. All other raw paths stay intact.
        target = raw
        parts = key.split(".")
        for part in parts[:-1]:
            if not isinstance(target.get(part), dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
        save_config(raw)
    else:
        save_config(patch, merge_existing=True, preserve_keys={tuple(key.split("."))})


@method("settings.get")
@_profile_scoped
def _settings_get(rid, params):
    from hermes_cli.config import _CONFIG_LOCK, require_readable_config_before_write
    from hermes_cli.web_server_config import _schema_with_dynamic_provider_options
    try:
        with _sessions_lock:
            session = _settings_session(params)
        # Plugin discovery can read config; never hold its locks under the config writer lock.
        schema = _schema_with_dynamic_provider_options()
        with _CONFIG_LOCK:
            fields = _settings_fields(require_readable_config_before_write(), schema)
        with _sessions_lock:
            _settings_session(params, session)
        return _ok(rid, {"fields": fields, "profile": _settings_profile()})
    except LookupError as exc:
        return _err(rid, 4001, str(exc))
    except Exception:
        return _err(rid, 5098, "Settings could not be read. Repair config.yaml or its permissions, then retry.")


@method("settings.set")
@_profile_scoped
def _settings_set(rid, params):
    from hermes_cli import managed_scope
    from hermes_cli.config import _CONFIG_LOCK, is_managed, require_readable_config_before_write
    from hermes_cli.web_server_config import _schema_with_dynamic_provider_options
    if not isinstance(params.get("key"), str) or "value" not in params:
        return _err(rid, 4000, "A text key and a JSON value are required.")
    if "confirmed" in params and type(params["confirmed"]) is not bool:
        return _err(rid, 4000, "confirmed must be a boolean.")
    key, value = params["key"], params["value"]
    try:
        if not params.get("session_id"):
            raise LookupError("A live settings session is required.")
        with _sessions_lock:
            session = _settings_session(params)
        # Discovery can take time. Revalidate the exact record and scoped home before any write.
        schema = _schema_with_dynamic_provider_options()
        if key not in schema:
            raise ValueError("Only declared settings fields can be changed.")
        with _sessions_lock:
            _settings_session(params, session)
            with _CONFIG_LOCK:
                pinned_keys = managed_scope.managed_config_keys()
                if is_managed() or any(path == pinned or path.startswith(pinned + ".") or pinned.startswith(path + ".")
                                       for path in _settings_write_paths(key) for pinned in pinned_keys):
                    raise ValueError("This setting is managed by your administrator.")
                raw = require_readable_config_before_write()
                old = _settings_leaf(raw, key)
                value = _settings_preserve_credentials(value, old, key)
                field = _settings_fields(raw, schema)[key]
                _settings_validate(key, params["value"], field)
                message = _settings_confirmation(key, value, field, _settings_profile())
                if value == old:
                    return _ok(rid, {"key": key, "value": field["value"],
                                     "confirm_required": False, "confirm_message": ""})
                if message and params.get("confirmed") is not True:
                    return _ok(rid, {"key": key, "confirm_required": True, "confirm_message": message})
                _settings_session(params, session)
                _settings_save(key, value, raw)
                canonical = _settings_fields(require_readable_config_before_write(), schema)[key]["value"]
        return _ok(rid, {"key": key, "value": canonical, "confirm_required": False, "confirm_message": ""})
    except LookupError as exc:
        return _err(rid, 4001, str(exc))
    except ValueError as exc:
        return _err(rid, 4002, str(exc))
    except Exception:
        return _err(rid, 5098, "The settings change could not be confirmed. Check config.yaml, its permissions and the selected model. Reload Settings before you retry.")


def register(server):
    bind_module(globals(), server)
