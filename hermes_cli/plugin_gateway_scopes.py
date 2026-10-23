"""Caller-bound, post-RPC gateway event leases for trusted in-process plugins.

No bearer identifier is serialised. Dispatchers capture the original peer and
subscription; this module validates owned events and observes delivery failure.
"""
from __future__ import annotations

import asyncio
import json
import math
import threading
from typing import Any, Callable

from hermes_cli.plugin_gateway_methods import looks_like_plugin_method


class GatewayScopeError(RuntimeError):
    """Secret-safe failure of a revoked or invalid scoped publisher."""


class GatewayScopeDeliveryError(GatewayScopeError):
    """The original transport did not acknowledge delivery."""


def _json_value(value: Any, *, depth: int = 0) -> bool:
    """Only genuine JSON; json.dumps alone coerces keys/tuples and allows NaN."""
    if depth > 64:
        return False
    if value is None or type(value) in (str, int, bool):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item, depth=depth + 1) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(item, depth=depth + 1)
                   for key, item in value.items())
    return False


class GatewayScopeAdmission:
    """A captured lease survives only a successfully completed RPC."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._settled = threading.Event()
        self._state = "pending"
        self._leases: list[GatewayScopeLease] = []

    def current(self) -> bool:
        with self._lock:
            return self._state != "revoked"

    def await_grant(self, handler_thread: int) -> bool:
        # A worker spawned by the handler can start before the RPC result.
        # Never send a provisional event for a handler that might fail.
        if threading.get_ident() == handler_thread and not self._settled.is_set():
            return False
        if not self._settled.wait(timeout=60):
            return False
        with self._lock:
            return self._state == "granted"

    def capture(
        self, *, plugin_id: str, session_id: str, profile: str,
        current: Callable[[], bool],
        deliver: Callable[[dict[str, Any], Callable[[], bool]], bool],
    ) -> GatewayScopeLease:
        with self._lock:
            if self._state != "pending":
                raise GatewayScopeError("gateway scope capture is no longer authorized")
            lease = GatewayScopeLease(
                plugin_id=plugin_id, session_id=session_id, profile=profile,
                admission=self, current=current, deliver=deliver,
                handler_thread=threading.get_ident(),
            )
            self._leases.append(lease)
            return lease

    def grant(self) -> None:
        with self._lock:
            if self._state == "pending":
                self._state = "granted"
                self._settled.set()

    def revoke(self) -> None:
        with self._lock:
            self._state = "revoked"
            self._settled.set()
            leases = tuple(self._leases)
        for lease in leases:
            lease.cancellation.set()


class GatewayScopeLease:
    """Opaque single-recipient publisher with an observable delivery contract.

    publish returns True after the original transport acknowledges a send, not
    after a client processes it. Rejection raises a secret-safe exception.
    close waits for the in-flight final publish, then revokes idempotently.
    """

    def __init__(
        self, *, plugin_id: str, session_id: str, profile: str,
        admission: GatewayScopeAdmission, current: Callable[[], bool],
        deliver: Callable[[dict[str, Any], Callable[[], bool]], bool],
        handler_thread: int,
    ) -> None:
        self._handler_thread = handler_thread
        self._plugin_id = plugin_id
        self._session_id = session_id
        self._profile = profile
        self._admission = admission
        self._current = current
        self._deliver = deliver
        self._publish_lock = threading.Lock()
        self._revoked = False
        self.cancellation = threading.Event()

    def _is_current(self) -> bool:
        if self._revoked or self.cancellation.is_set() or not self._admission.current():
            self._revoked = True
            self.cancellation.set()
            return False
        try:
            valid = bool(self._current())
        except Exception:
            valid = False
        if not valid:
            self._revoked = True
            self.cancellation.set()
        return valid

    def assert_current(self) -> None:
        if not self._is_current():
            raise GatewayScopeError("gateway scope is no longer authorized")

    def publish(self, event_name: str, payload: dict[str, Any]) -> bool:
        """Deliver one owned JSON-object event to the original peer only."""
        if not (looks_like_plugin_method(event_name)
                and event_name.startswith(f"{self._plugin_id}.")):
            raise GatewayScopeError("event name must belong to the registering plugin")
        if type(payload) is not dict or not _json_value(payload):
            raise GatewayScopeError("plugin event payload must be a finite JSON object")
        try:
            encoded = json.dumps(payload, allow_nan=False, ensure_ascii=False)
            if len(encoded.encode("utf-8")) > 256 * 1024:
                raise GatewayScopeError("plugin event payload exceeds 256 KiB")
            data = json.loads(encoded)
        except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
            raise GatewayScopeError("plugin event payload is not valid JSON") from exc
        frame = {"jsonrpc": "2.0", "method": "event", "params": {
            "type": "plugin.event", "session_id": self._session_id,
            "payload": {"plugin": self._plugin_id, "event_name": event_name,
                        "profile": self._profile, "data": data},
        }}
        # Await RPC settlement outside the delivery lock: a handler may close
        # a lease before returning while a spawned worker waits to publish.
        if not self._admission.await_grant(self._handler_thread):
            raise GatewayScopeError("gateway scope request did not complete successfully")
        with self._publish_lock:
            self.assert_current()
            try:
                delivered = self._deliver(frame, self._is_current)
            except Exception as exc:
                self._revoked = True
                self.cancellation.set()
                raise GatewayScopeDeliveryError("scoped event delivery failed") from exc
            if not delivered:
                self._revoked = True
                self.cancellation.set()
                raise GatewayScopeDeliveryError("scoped event delivery rejected")
            return True

    def close(self) -> None:
        """Revoke after any currently admitted publish completes."""
        with self._publish_lock:
            self._revoked = True
            self.cancellation.set()


async def _send_on_owner_loop(transport, frame: dict, current: Callable[[], bool]) -> bool:
    """Check again at actual WS send after queued frames and send-lock waits."""
    if not current():
        return False
    guarded_send = getattr(transport, "write_many_if_current_async", None)
    if callable(guarded_send):
        checked = False

        def guard() -> bool:
            nonlocal checked
            checked = current()
            return checked

        sent = await guarded_send([frame], guard)
        return bool(checked and sent)
    return bool(current() and transport.write(frame))


def deliver_on_owner_loop(
    transport, loop: asyncio.AbstractEventLoop, frame: dict,
    current: Callable[[], bool],
) -> bool:
    """No session fanout or replacement viewer lookup."""
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is loop:
        raise GatewayScopeDeliveryError("scoped publish requires a worker thread")
    future = asyncio.run_coroutine_threadsafe(
        _send_on_owner_loop(transport, frame, current), loop,
    )
    return bool(future.result())


def deliver_legacy(
    transport, frame: dict, current: Callable[[], bool],
) -> bool:
    """Pinned legacy peer: WS uses its owner loop; stdio writes synchronously."""
    loop = getattr(transport, "_loop", None)
    if loop is not None:
        return deliver_on_owner_loop(transport, loop, frame, current)
    return bool(current() and transport.write(frame))
