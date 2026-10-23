"""Validated, profile-local plugin JSON-RPC registrations (not core RPC contracts)."""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel

# Three or more dotted segments: the first belongs to the registering plugin and
# the rest name its own surface. Never normalize a caller-controlled method name.
_SEGMENT = r"[a-z][a-z0-9_-]*"
_METHOD = re.compile(rf"{_SEGMENT}(?:\\.{_SEGMENT}){{2,}}\\Z")


@dataclass(frozen=True)
class GatewayRequestContext:
    """Server-authorized snapshot, not a bearer token or a mutable session/transport."""

    session_id: str
    profile: str
    _attached: Callable[[], bool] = field(repr=False, compare=False)

    def assert_attached(self) -> None:
        """Recheck the live session generation and caller transport before a side effect."""
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
    if (not callable(handler) or inspect.iscoroutinefunction(handler)
            or inspect.isasyncgenfunction(handler)
            or inspect.iscoroutinefunction(getattr(handler, "__call__", None))):
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
