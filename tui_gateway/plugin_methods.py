"""Session-authorized plugin RPC dispatch outside the static core method catalog.

Imported by the RPC dispatcher on demand. Plugin callbacks retain their original
module globals: method_ctx.bind_module must never rebind them.
"""

from __future__ import annotations

import logging
import threading

from hermes_cli.backend_retirement import retirement
from hermes_cli.plugin_gateway_methods import (
    GatewayCallerBinding, GatewayMethodFailure, GatewayRequestContext,
    invoke_gateway_method, registered_gateway_methods,
)
from hermes_cli.plugin_gateway_scopes import GatewayScopeAdmission, deliver_legacy
from tui_gateway.transport import current_transport

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
    transport = current_transport()
    owner_loop = getattr(transport, "_loop", None)
    profile_home = session.get("profile_home")
    admission = GatewayScopeAdmission()
    active = threading.Event()
    active.set()
    succeeded = False
    # Pin the real membership lifetime, including before direct-to-fanout
    # promotion, rather than accepting SID/profile or socket equality.
    with server._sessions_lock:
        attachment = server._plugin_gateway_attachment(session, transport)
    if attachment is None:
        return server._err(rid, 4001, "session is no longer attached")
    generation = (session.get("session_key"), session.get("execution_generation"),
                  session.get("runtime_generation"))
    profile = (profile_name_for_home(profile_home or server._hermes_home)
               or server._current_profile_name())
    binding = GatewayCallerBinding(
        connection=None, actor=None, transport=transport, session=session,
        subscription=None, attachment=attachment, session_id=sid,
        profile=profile, generation=generation, epoch=None, profile_home=profile_home,
    )

    def attached() -> bool:
        # A captured legacy scope cannot survive process drain/retirement, even
        # when its original session and socket remain temporarily attached.
        with retirement.work() as admitted:
            if not admitted or transport is None or getattr(transport, "closed", False):
                return False
            with server._sessions_lock:
                if (server._sessions.get(sid) is not session
                        or session.get("profile_home") != profile_home
                        or (session.get("session_key"), session.get("execution_generation"),
                            session.get("runtime_generation")) != generation
                        or not server._session_transport_contains(session, transport)):
                    return False
                current = server._plugin_gateway_attachment(session, transport)
                return (current is not None and current[0] is attachment[0]
                        and current[1] == attachment[1])

    def deliver(frame, current):
        # Hold the real backend retirement permit through the transport send,
        # not only at scheduling time (no check/use gap).
        with retirement.work() as admitted:
            return admitted and deliver_legacy(transport, frame, current)

    def capture(plugin_id, registered, caller_binding):
        if caller_binding is not binding or not active.is_set() or not attached():
            raise PermissionError("gateway scope capture is unavailable")
        return admission.capture(
            plugin_id=plugin_id, session_id=sid,
            owner_loop=owner_loop, caller_binding=caller_binding,
            profile=profile,
            current=lambda: attached() and registered(),
            deliver=deliver,
        )

    context = GatewayRequestContext(
        session_id=sid,
        profile=profile,
        _attached=lambda: active.is_set() and attached(),
        _capture_scope=capture, _owner_loop=owner_loop,
        _caller_binding=binding,
    )
    try:
        with server._session_profile_runtime_scope({"profile_home": profile_home}):
            result = invoke_gateway_method(name, context, params)
        admission.grant()
        succeeded = True
        return server._ok(rid, result)
    except GatewayMethodFailure as exc:
        return server._err(rid, exc.code, exc.message)
    except Exception:
        logger.exception("plugin gateway method failed: %s", name)
        return server._err(rid, -32000, "plugin gateway method failed")
    finally:
        if not succeeded:
            admission.revoke()
        active.clear()
