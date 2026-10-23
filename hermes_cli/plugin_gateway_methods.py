"""Validated, profile-local plugin JSON-RPC registrations (not core RPC contracts)."""

from __future__ import annotations

import asyncio
import inspect
import re
import threading
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable

from pydantic import BaseModel

# Three or more dotted segments: the first belongs to the registering plugin and
# the rest name its own surface. Never normalize a caller-controlled method name.
_SEGMENT = r"[a-z][a-z0-9_-]*"
_METHOD = re.compile(rf"{_SEGMENT}(?:\.{_SEGMENT}){{2,}}\Z")


def _is_transport_owner_loop(loop: asyncio.AbstractEventLoop | None) -> bool:
    """Identify unsupported blocking calls without consulting transport or DB locks."""
    if loop is None:
        return False
    try:
        return asyncio.get_running_loop() is loop
    except RuntimeError:
        return False


@dataclass(frozen=True)
class GatewayRequestContext:
    """Server-authorized snapshot, not a bearer token or a mutable session/transport."""

    session_id: str
    profile: str
    _attached: Callable[[], bool] = field(repr=False, compare=False)
    _capture_scope: Callable[[], Any] | None = field(
        default=None, repr=False, compare=False,
    )
    _owner_loop: asyncio.AbstractEventLoop | None = field(
        default=None, repr=False, compare=False,
    )

    def capture_scope(self):
        """Capture a durable publisher only inside its authorized registered handler."""
        self.assert_attached()
        if self._capture_scope is None:
            raise PermissionError("gateway scope capture is unavailable")
        return self._capture_scope()

    def assert_attached(self) -> None:
        """Recheck authority from a worker, never blocking the transport owner loop."""
        if _is_transport_owner_loop(self._owner_loop):
            raise RuntimeError(
                "gateway request authority check requires a worker thread; "
                "use await asyncio.to_thread(request.assert_attached)"
            )
        if not self._attached():
            raise PermissionError("gateway session detached or replaced")


@dataclass(frozen=True)
class GatewayMethod:
    name: str
    plugin_id: str
    handler: Callable[[GatewayRequestContext, dict[str, Any]], dict[str, Any]]
    schema: type[BaseModel] | None = None


def looks_like_plugin_method(name: str) -> bool:
    """Only a shape probe; actual ownership is enforced by registration."""
    return isinstance(name, str) and _METHOD.fullmatch(name) is not None


def validate_gateway_registration(
    plugin_id: str, name: str, handler: Callable, schema: type[BaseModel] | None,
) -> GatewayMethod:
    """Reject unowned/core names, non-sync handlers and unenforceable parameter schemas."""
    if not isinstance(plugin_id, str) or re.fullmatch(_SEGMENT, plugin_id) is None:
        raise ValueError("plugin registry key is not a valid gateway namespace")
    if not looks_like_plugin_method(name) or not name.startswith(f"{plugin_id}."):
        raise ValueError(f"gateway method must begin with owned namespace {plugin_id!r} and two dotted segments")
    from tui_gateway.contracts.registry import METHODS, CANONICAL_METHODS
    if name in METHODS or name in CANONICAL_METHODS:
        raise ValueError(f"gateway method {name!r} collides with a core method")
    if not callable(handler):
        raise TypeError("gateway handler must be a synchronous callable")
    # functools.partial can hide an async callable object's implementation
    # from inspect.iscoroutinefunction() / inspect.isasyncgenfunction().
    target = handler
    while isinstance(target, partial):
        target = target.func
    call_impl = type(target).__call__
    if (inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(target)
            or inspect.iscoroutinefunction(call_impl) or inspect.isasyncgenfunction(call_impl)):
        raise TypeError("gateway handler must be a synchronous callable")
    try:
        inspect.signature(handler).bind(object(), {})
    except (TypeError, ValueError) as exc:
        raise TypeError("gateway handler must accept (request: GatewayRequestContext, params: dict)") from exc
    if schema is not None and (
        not isinstance(schema, type) or not issubclass(schema, BaseModel)
        or schema.model_config.get("extra") != "forbid"
    ):
        raise TypeError("gateway schema must be a Pydantic BaseModel class with extra='forbid'")
    return GatewayMethod(name=name, plugin_id=plugin_id, handler=handler, schema=schema)

class GatewayMethodFailure(Exception):
    """A secret-safe JSON-RPC failure shared by the legacy and canonical transports."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def registered_gateway_methods() -> list[str]:
    """Discover only the current profile manager's live registrations."""
    from hermes_cli.plugins import discover_plugins, get_plugin_manager

    discover_plugins()
    return sorted(get_plugin_manager()._gateway_methods)


def invoke_gateway_method(name: str, request: GatewayRequestContext, params: dict) -> dict:
    """Call one profile-owned synchronous handler without rebinding its module globals.

    Both transports provide their own attachment/actor fence in *request*. A
    disposable registration adds another fence for in-flight unload/reload.
    """
    import json
    import logging
    from dataclasses import replace

    from pydantic import ValidationError

    from hermes_cli.plugins import discover_plugins, get_plugin_manager

    try:
        request.assert_attached()
        discover_plugins()
        request.assert_attached()
        manager = get_plugin_manager()
        entry = manager._gateway_methods.get(name)
        if entry is None:
            raise GatewayMethodFailure(-32601, f"unknown method: {name}")

        # A callback's own assert_attached also refuses a registration retired
        # during execution, before it performs any further side effect.
        # Reuse this exact registration identity even if another plugin registers
        # the same name after unload. A leaked request cannot mint a scope later.
        running = False
        handler_thread = threading.get_ident()

        def registered() -> bool:
            return manager._gateway_methods.get(name) is entry

        def capture():
            if not running or threading.get_ident() != handler_thread:
                raise PermissionError("gateway scope capture requires an active registered handler")
            context.assert_attached()
            if request._capture_scope is None:
                raise PermissionError("gateway scope capture is unavailable")
            return request._capture_scope(entry.plugin_id, registered)

        context = replace(
            request, _attached=lambda: request._attached() and registered(),
            _capture_scope=capture,
        )
        if entry.schema is None:
            validated = dict(params)
        else:
            try:
                validated = entry.schema.model_validate(params, strict=True).model_dump(mode="json")
            except ValidationError as exc:
                fields = ", ".join(
                    f"{'.'.join(map(str, item['loc'])) or 'params'}: {item['type']}"
                    for item in exc.errors(include_input=False, include_url=False)
                )
                raise GatewayMethodFailure(-32602, f"invalid plugin params: {fields}") from exc

        context.assert_attached()
        running = True
        try:
            result = entry.handler(context, validated)
        finally:
            running = False
        context.assert_attached()
        if not isinstance(result, dict):
            raise TypeError("gateway method result must be a JSON object")
        json.dumps(result, allow_nan=False)
        return result
    except GatewayMethodFailure:
        raise
    except PermissionError as exc:
        raise GatewayMethodFailure(4001, "session is no longer attached") from exc
    except Exception as exc:
        logging.getLogger(__name__).exception("plugin gateway method failed: %s", name)
        raise GatewayMethodFailure(-32000, "plugin gateway method failed") from exc
