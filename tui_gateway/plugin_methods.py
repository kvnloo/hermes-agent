"""Session-authorized plugin RPC dispatch outside the static core method catalog.

Imported by the RPC dispatcher on demand. Plugin callbacks retain their original
module globals: method_ctx.bind_module must never rebind them.
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from hermes_cli.plugin_gateway_methods import GatewayRequestContext

logger = logging.getLogger(__name__)


def authorize_session(rid, params: dict):
    """Live attachment, not untrusted session_id/profile text, grants access."""
    from tui_gateway import server

    if "profile" in params:
        return None, server._err(rid, 4001, "profile selection is not authorized for plugin RPCs")
    sid = params.get("session_id")
    if not isinstance(sid, str) or not sid:
        return None, server._err(rid, 4001, "attached session_id required")
    _, session = server._current_session_steer_authority(sid)
    if session is None:
        return None, server._err(rid, 4001, "session is detached, foreign or replaced")
    return session, None


def list_plugin_methods(rid, params: dict) -> tuple[list[str], dict | None]:
    """Only names for the calling live session's profile; never callbacks or schemas."""
    from tui_gateway import server
    from hermes_cli.plugins import discover_plugins, get_plugin_manager

    if params.get("session_id") is None:
        return [], None  # legacy sessionless build probe carries no plugin authority
    session, problem = authorize_session(rid, params)
    if problem is not None:
        return [], problem
    try:
        with server._session_profile_runtime_scope({"profile_home": session.get("profile_home")}):
            discover_plugins()  # joins/initializes discovery on the RPC worker, never on the reader
            if server._current_session_steer_authority(params["session_id"])[1] is not session:
                return [], server._err(rid, 4001, "session is no longer attached")
            return sorted(get_plugin_manager()._gateway_methods), None
    except Exception:
        logger.exception("gateway plugin capability lookup failed")
        return [], server._err(rid, -32000, "gateway plugin capability lookup failed")


def dispatch_plugin_method(rid, name: str, params: dict) -> dict:
    """Run a registered handler with profile + transport preserved by the RPC pool."""
    from hermes_constants import profile_name_for_home
    from hermes_cli.plugins import discover_plugins, get_plugin_manager
    from tui_gateway import server

    session, problem = authorize_session(rid, params)
    if problem is not None:
        return problem
    sid = params["session_id"]

    def attached() -> bool:
        return server._current_session_steer_authority(sid)[1] is session

    try:
        with server._session_profile_runtime_scope({"profile_home": session.get("profile_home")}):
            discover_plugins()
            manager = get_plugin_manager()
            entry = manager._gateway_methods.get(name)
            if entry is None:
                return server._err(rid, -32601, f"unknown method: {name}")
            if entry.schema is not None:
                try:
                    validated = entry.schema.model_validate(params, strict=True).model_dump(mode="json")
                except ValidationError as exc:
                    fields = ", ".join(
                        f"{'.'.join(map(str, item['loc'])) or 'params'}: {item['type']}"
                        for item in exc.errors(include_input=False, include_url=False)
                    )
                    return server._err(rid, -32602, f"invalid plugin params: {fields}")
            else:
                validated = dict(params)
            context = GatewayRequestContext(
                session_id=sid,
                profile=profile_name_for_home(session.get("profile_home") or server._hermes_home)
                        or server._current_profile_name(),
                _attached=attached,
            )
            context.assert_attached()
            result = entry.handler(context, validated)
            context.assert_attached()
            if manager._gateway_methods.get(name) is not entry:
                return server._err(rid, -32601, f"unknown method: {name}")
            if not isinstance(result, dict):
                raise TypeError("gateway method result must be a JSON object")
            json.dumps(result, allow_nan=False)
            return server._ok(rid, result)
    except PermissionError:
        return server._err(rid, 4001, "session is no longer attached")
    except Exception:
        logger.exception("plugin gateway method failed: %s", name)
        return server._err(rid, -32000, "plugin gateway method failed")
