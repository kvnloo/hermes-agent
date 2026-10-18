"""Read-only MCP/SSH sheets over Hermes authorities, not OMP config files."""
from .method_ctx import HandlerRegistry, bind_module

_registry = HandlerRegistry()
method = _registry.method


def _operations_auth_details(name, cfg):
    # Never forward URLs, command/args, env/header values, OAuth tokens or key paths.
    from hermes_cli.mcp_config import _oauth_tokens_present
    if cfg.get("auth") == "oauth":
        return "OAuth tokens present" if _oauth_tokens_present(name) else "OAuth tokens absent"
    if cfg.get("headers"):
        return "Headers configured (values withheld)"
    if cfg.get("env"):
        return "Environment configured (values withheld)"
    return "Auth configured (details withheld)" if cfg.get("auth") else "No explicit auth configured"


def _operations_mcp(view):
    from agent.secret_scope import is_multiplex_active
    from hermes_constants import get_process_hermes_home, hermes_home_key
    from tools.mcp_tool_discovery import get_mcp_status
    from tools.mcp_tool_common import mcp_server_enabled

    configured, plugins = _mcp_server_rows()
    include_runtime = is_multiplex_active() or hermes_home_key() == hermes_home_key(get_process_hermes_home())
    if view == "mcp-list":
        return [{"name": name, "details": [
            "HTTP" if cfg.get("url") else "stdio" if cfg.get("command") else "unknown transport",
            "enabled" if mcp_server_enabled(cfg) else "disabled",
            "plugin" if plugins.get(name) is not None else "config",
            _operations_auth_details(name, cfg)]} for name, cfg in sorted(configured.items())]
    statuses = get_mcp_status(configured, include_runtime=include_runtime)
    if view == "mcp-status":
        # Runtime errors can contain secrets. Only closed status labels/counts leave the backend.
        return [{"name": row["name"], "details": [row["status"], f"{row['tools']} cached tools"]}
                for row in statuses]
    return _operations_mcp_tools(configured, include_runtime)


def _operations_mcp_tools(configured, include_runtime):
    from tools import mcp_tool as core
    from tools.mcp_tool_scope import _key_visible_in_scope, _resolve_server_key

    rows = []
    with core._lock:
        scope = core._mcp_registry_scope()
        for name in sorted(configured):
            key = _resolve_server_key(name)
            names = []
            if include_runtime and _key_visible_in_scope(key, scope):
                server = core._servers.get(key)
                names = list(server._registered_tool_names) if server else list(core._lazy_server_tool_names.get(key, []))
            rows.append({"name": name, "details": sorted(names) or ["No cached tools available; no connection was attempted."]})
    return rows


def _operations_catalog(view):
    from hermes_cli import mcp_catalog
    return [{"name": entry.name, "details": [
        "installed" if mcp_catalog.is_installed(entry.name) else "not installed",
        "enabled" if mcp_catalog.is_enabled(entry.name) else "disabled"]}
        for entry in mcp_catalog.list_catalog()]


def _operations_ssh(view):
    import ipaddress
    import re
    from tools.terminal_tool_config import _tenv

    host = _tenv("TERMINAL_SSH_HOST").strip()
    if not host:
        return []
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", host):
            raise ValueError("invalid SSH target")
    user = _tenv("TERMINAL_SSH_USER").strip()
    if user and not re.fullmatch(r"[A-Za-z0-9_.-]+", user):
        raise ValueError("invalid SSH user")
    port = int(_tenv("TERMINAL_SSH_PORT", "22") or "22")
    if not 1 <= port <= 65535:
        raise ValueError("invalid SSH port")
    return [{"name": host, "details": [f"User: {user or '(SSH default)'}", f"Port: {port}",
             "Identity configured (path withheld)" if _tenv("TERMINAL_SSH_KEY") else "SSH agent / default identity",
             "Active SSH backend" if _tenv("TERMINAL_ENV", "local") == "ssh" else "Configured target; SSH backend is not active",
             "Connection not probed"]}]


_OPERATIONS_READERS = {"mcp-list": _operations_mcp, "mcp-status": _operations_mcp,
                       "mcp-tools": _operations_mcp, "mcp-catalog": _operations_catalog,
                       "ssh-list": _operations_ssh}
_OPERATIONS_MESSAGES = {
    "mcp-list": "Configured MCP servers from this Hermes profile. Credential values and launch arguments are withheld.",
    "mcp-status": "Cached runtime status only; this report does not connect, probe, reload or authenticate.",
    "mcp-tools": "Cached registered tool names only, including lazy registrations. No server is started or probed.",
    "mcp-catalog": "Hermes MCP catalog inventory only. This sheet cannot install, enable or authenticate servers.",
    "ssh-list": "Hermes supports one configured SSH terminal target per profile. This is not an OpenSSH/OMP host inventory. "
                "SSH host add/remove, reconnect and authentication management are unsupported in this native sheet."
}


@method("operations.report")
def _operations_report(rid, params):
    from pydantic import ValidationError
    from tui_gateway.contracts.operations import OperationalReportParams
    try:
        params = OperationalReportParams.model_validate(params).model_dump(mode="json")
    except ValidationError:
        return _err(rid, 4000, "A live session and a supported read-only inventory view are required; profile overrides are not accepted.")
    sid = params["session_id"]
    _, owner = _current_session_steer_authority(sid)
    if owner is None:
        return _err(rid, 4001, "session not found or not owned by this transport")
    with _session_profile_runtime_scope(owner):
        # Reject a retired/deleted session or a profile switch before touching inventory.
        try:
            _settings_session(params, expected=owner)
        except LookupError:
            return _err(rid, 4001, "operational report session is no longer available")
        view = params["view"]
        scope = _settings_profile()
        result = {"view": view, "scope": scope, "state": "ready", "read_only": True,
                  "rows": [], "message": _OPERATIONS_MESSAGES[view]}
        try:
            result["rows"] = _OPERATIONS_READERS[view](view)
        except Exception:
            # Exception strings and probe output are not safe auth detail surfaces.
            logger.debug("Operational %s report unavailable", view, exc_info=True)
            result.update(state="unavailable", message="Hermes inventory service is unavailable. No connection or mutation was attempted.")
        if _current_session_steer_authority(sid)[1] is not owner:
            return _err(rid, 4001, "operational report session changed during the read")
        try:
            _settings_session(params, expected=owner)
        except LookupError:
            return _err(rid, 4001, "operational report profile changed during the read")
        return _ok(rid, result)


def register(server):
    bind_module(globals(), server)
    server._LONG_HANDLERS = server._LONG_HANDLERS | _registry.names()
