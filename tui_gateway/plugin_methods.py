"""Session-authorized plugin RPC dispatch outside the static core method catalog.

Imported by the RPC dispatcher on demand. Plugin callbacks retain their original
module globals: method_ctx.bind_module must never rebind them.
"""

from __future__ import annotations

import logging

from hermes_cli.plugin_gateway_methods import (
    GatewayMethodFailure, GatewayRequestContext, invoke_gateway_method, registered_gateway_methods,
)

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
    if "profile" in params:
        return [], server._err(rid, 4001, "profile selection is not authorized for plugin RPCs")
    if params.get("session_id") is None:
        return [], None  # legacy sessionless build probe carries no plugin authority
    session, problem = authorize_session(rid, params)
    if problem is not None:
        return [], problem
    try:
        with server._session_profile_runtime_scope({"profile_home": session.get("profile_home")}):
            methods = registered_gateway_methods()  # worker joins discovery, never the reader
            if server._current_session_steer_authority(params["session_id"])[1] is not session:
                return [], server._err(rid, 4001, "session is no longer attached")
            return methods, None
    except Exception:
        logger.exception("gateway plugin capability lookup failed")
        return [], server._err(rid, -32000, "gateway plugin capability lookup failed")


def dispatch_plugin_method(rid, name: str, params: dict) -> dict:
    """Run a registered handler with profile + transport preserved by the RPC pool."""
    from hermes_constants import profile_name_for_home
    from tui_gateway import server

    session, problem = authorize_session(rid, params)
    if problem is not None:
        return problem
    sid = params["session_id"]

    def attached() -> bool:
        return server._current_session_steer_authority(sid)[1] is session

    context = GatewayRequestContext(
        session_id=sid,
        profile=profile_name_for_home(session.get("profile_home") or server._hermes_home)
                or server._current_profile_name(),
        _attached=attached,
    )
    try:
        with server._session_profile_runtime_scope({"profile_home": session.get("profile_home")}):
            return server._ok(rid, invoke_gateway_method(name, context, params))
    except GatewayMethodFailure as exc:
        return server._err(rid, exc.code, exc.message)
    except Exception:
        logger.exception("plugin gateway method failed: %s", name)
        return server._err(rid, -32000, "plugin gateway method failed")
