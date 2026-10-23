"""Canonical hermes-gateway-v1 admission for the shared plugin gateway-method seam.

The authority owns identity, capabilities, subscriptions and session generations;
the existing per-profile PluginManager owns registrations. No sidecar runtime is
created and plugin callbacks retain their defining module globals.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from gateway.session_authorities import owner_scope, require_serving, served_profile_name
from gateway.session_contract import SessionRef
from hermes_cli.plugin_gateway_methods import (
    GatewayMethodFailure, GatewayRequestContext, invoke_gateway_method,
    looks_like_plugin_method, registered_gateway_methods,
)
from hermes_cli.plugin_gateway_scopes import GatewayScopeAdmission, deliver_on_owner_loop
from hermes_state_runtime import RuntimeStoreError

logger = logging.getLogger(__name__)


def is_plugin_request(method, core_handlers) -> bool:
    """Let *all* declared/core methods keep their original authority and dispatch."""
    if method == "gateway.capabilities":
        return True
    if not looks_like_plugin_method(method):
        return False
    from tui_gateway.contracts.registry import CANONICAL_METHODS, METHODS
    from gateway.session_group_controls import GROUP_METHODS

    return (method not in METHODS and method not in CANONICAL_METHODS
            and method not in GROUP_METHODS and method not in core_handlers())


def _context(
    connection, params: dict, active: threading.Event,
    admission: GatewayScopeAdmission, loop: asyncio.AbstractEventLoop,
) -> GatewayRequestContext:
    """Freeze the caller's actual subscription, live object and DB generation."""
    sid = params.get("session_id")
    if not isinstance(sid, str) or not sid:
        raise GatewayMethodFailure(4001, "attached session_id required")

    authority, actor, transport = connection.authority, connection.actor, connection.transport
    require_serving(authority)
    authority._require_admission_open()
    subscription = connection.subscriptions.get(sid)
    live = authority.sessions.get(sid)
    if (connection._closed or not active.is_set()
            or getattr(transport, "closed", False)
            or actor.profile_id != authority.profile_id
            or "session:control" not in actor.capabilities
            or not subscription or live is None
            or live.subscribers.get(subscription) is not actor
            or authority.events.get(actor.transport_id) is not transport):
        raise GatewayMethodFailure(4001, "session is detached, foreign or read-only")

    ref = SessionRef(authority.profile_id, sid)
    authority.authorize(actor, ref, "session:control")
    row = authority.db.get_session(sid)
    if row is None:
        raise GatewayMethodFailure(4001, "session is no longer attached")
    generation, epoch = row["runtime_generation"], authority.epoch

    def attached_in_memory() -> bool:
        """Cheap loop-safe ownership fence (no DB or token-counter flushing)."""
        if (connection._closed
                or getattr(transport, "closed", False)
                or getattr(authority, "retiring", False) or getattr(authority, "retired", False)
                or getattr(authority.runner, "_draining", False)
                or authority.epoch != epoch or actor.profile_id != authority.profile_id
                or "session:control" not in actor.capabilities
                or authority.events.get(actor.transport_id) is not transport
                or connection.subscriptions.get(sid) != subscription
                or authority.sessions.get(sid) is not live
                or live.subscribers.get(subscription) is not actor
                or live.superseded):
            return False
        return True

    def attached() -> bool:
        if not attached_in_memory():
            return False
        current = authority.db.get_session(sid)
        return current is not None and current["runtime_generation"] == generation

    # The RPC context stays request-bound; only a captured lease drops the
    # request-active fence, keeping the original actor, subscription and runtime.
    profile = served_profile_name(authority.profile_id)

    def capture(plugin_id, registered):
        if not active.is_set() or not attached():
            raise PermissionError("gateway scope capture is unavailable")
        return admission.capture(
            plugin_id=plugin_id, session_id=sid, profile=profile,
            current=lambda: attached() and registered(),
            deliver=lambda frame, current: deliver_on_owner_loop(
                transport, loop, frame, current,
                current_on_loop=lambda: attached_in_memory() and registered(),
            ),
        )

    return GatewayRequestContext(
        session_id=sid, profile=profile,
        _attached=lambda: active.is_set() and attached(),
        _capture_scope=capture,
    )


def _execute(
    connection, method: str, params: dict, active: threading.Event,
    admission: GatewayScopeAdmission, loop: asyncio.AbstractEventLoop,
) -> dict:
    """Do discovery, validation, callbacks and scope-bound checks off the owner loop."""
    if "profile" in params:
        raise GatewayMethodFailure(4001, "profile selection is not authorized for plugin RPCs")
    if method == "gateway.capabilities" and set(params) - {"session_id"}:
        raise RuntimeStoreError("invalid_params")
    from hermes_cli.active_sessions import PER_SESSION_EXCLUSIVE_SUBMIT

    if method == "gateway.capabilities" and params.get("session_id") is None:
        return {"per_session_exclusive_submit": bool(PER_SESSION_EXCLUSIVE_SUBMIT),
                "plugin_methods": []}

    with owner_scope(connection.authority):
        context = _context(connection, params, active, admission, loop)
        context.assert_attached()
        if method == "gateway.capabilities":
            methods = registered_gateway_methods()
            context.assert_attached()
            return {"per_session_exclusive_submit": bool(PER_SESSION_EXCLUSIVE_SUBMIT),
                    "plugin_methods": methods}
        return invoke_gateway_method(method, context, params)


async def dispatch_plugin_request(connection, rid, method: str, params: dict) -> dict:
    """One canonical JSON-RPC reply through the authenticated authority connection."""
    active = threading.Event()
    active.set()
    admission = GatewayScopeAdmission()
    succeeded = False
    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.to_thread(
            _execute, connection, method, params, active, admission, loop,
        )
        admission.grant()
        succeeded = True
        return {"jsonrpc": "2.0", "id": rid, "result": result}
    except GatewayMethodFailure as exc:
        return {"jsonrpc": "2.0", "id": rid, "error": {
            "code": exc.code, "message": exc.message}}
    except RuntimeStoreError as exc:
        from gateway.session_controls import _log_refusal, _refusal_data
        _log_refusal(connection.actor.profile_id, method, exc)
        return {"jsonrpc": "2.0", "id": rid, "error": {
            "code": 4001, "message": exc.reason, "data": _refusal_data(exc)}}
    except Exception:
        logger.exception("canonical plugin gateway RPC failed: %s", method)
        return {"jsonrpc": "2.0", "id": rid, "error": {
            "code": -32000, "message": "plugin gateway method failed"}}
    finally:
        # Failed/cancelled admission invalidates every captured publisher. A
        # normal return revokes only this request's assert_attached, not leases.
        if not succeeded:
            admission.revoke()
        active.clear()
