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

from hermes_cli.plugin_gateway_methods import _is_transport_owner_loop, looks_like_plugin_method


class GatewayScopeError(RuntimeError):
    """Secret-safe failure of a revoked or invalid scoped publisher."""


class GatewayScopeDeliveryError(GatewayScopeError):
    """The original transport did not acknowledge delivery."""


def _json_value(value: Any) -> bool:
    """Only genuine JSON; json.dumps alone coerces keys/tuples and allows NaN."""
    if value is None or type(value) in (str, int, bool):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(item)
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
        if not self._settled.wait():
            return False
        with self._lock:
            return self._state == "granted"

    def capture(
        self, *, plugin_id: str, session_id: str, profile: str,
        current: Callable[[], bool],
        deliver: Callable[[dict[str, Any], Callable[[], bool]], bool],
        owner_loop: asyncio.AbstractEventLoop | None = None,
    ) -> GatewayScopeLease:
        with self._lock:
            if self._state != "pending":
                raise GatewayScopeError("gateway scope capture is no longer authorized")
            lease = GatewayScopeLease(
                plugin_id=plugin_id, session_id=session_id, profile=profile,
                admission=self, current=current, deliver=deliver,
                handler_thread=threading.get_ident(), owner_loop=owner_loop,
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
    Blocking operations reject the transport owner loop before taking locks.
    """

    def __init__(
        self, *, plugin_id: str, session_id: str, profile: str,
        admission: GatewayScopeAdmission, current: Callable[[], bool],
        deliver: Callable[[dict[str, Any], Callable[[], bool]], bool],
        handler_thread: int,
        owner_loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._handler_thread = handler_thread
        self._owner_loop = owner_loop
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

    def _require_worker_thread(self, operation: str) -> None:
        if _is_transport_owner_loop(self._owner_loop):
            usage = ("await asyncio.to_thread(lease.publish, event_name, payload)"
                     if operation == "publish" else
                     f"await asyncio.to_thread(lease.{operation})")
            raise GatewayScopeError(
                f"scoped {operation} requires a worker thread; use {usage}"
            )

    def assert_current(self) -> None:
        self._require_worker_thread("assert_current")
        if not self._is_current():
            raise GatewayScopeError("gateway scope is no longer authorized")

    def publish(self, event_name: str, payload: dict[str, Any]) -> bool:
        """Deliver one owned JSON-object event to the original peer only."""
        self._require_worker_thread("publish")
        if not (looks_like_plugin_method(event_name)
                and event_name.startswith(f"{self._plugin_id}.")):
            raise GatewayScopeError("event name must belong to the registering plugin")
        try:
            valid_json = type(payload) is dict and _json_value(payload)
        except RecursionError:
            valid_json = False
        if not valid_json:
            raise GatewayScopeError("plugin event payload must be a finite JSON object")
        try:
            data = json.loads(json.dumps(payload, allow_nan=False, ensure_ascii=False))
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
        """Worker-only drain and revocation; never block the transport owner loop."""
        self._require_worker_thread("close")
        with self._publish_lock:
            self._revoked = True
            self.cancellation.set()


async def _send_on_owner_loop(
    transport, frame: dict, current: Callable[[], bool],
    current_on_loop: Callable[[], bool] | None = None,
    generation_gate: asyncio.Lock | None = None,
) -> bool:
    """Fence in the real WS send lock; blocking authority checks run on workers.

    In particular, DB.get_session drains token accounting and can wait several
    seconds. Never invoke that check on the connection's event loop.
    """
    guarded_send = getattr(transport, "write_many_if_current_async", None)
    if callable(guarded_send):
        checked = False

        async def guard() -> bool:
            nonlocal checked
            checked = bool(await asyncio.to_thread(current))
            # While the DB check was yielding to a worker, detach/unload
            # might have run on the owner loop. Recheck cheap live ownership
            # immediately before send, still inside the real output lock.
            if checked and current_on_loop is not None:
                try:
                    checked = bool(current_on_loop())
                except Exception:
                    checked = False
            return checked

        if generation_gate is not None:
            # A valid worker read can race a rewind before the send. The
            # second, final read under the native mutation gate authorizes it.
            # Rewind/reset/compress and FIFO claims hold that same gate.
            if not await asyncio.to_thread(current):
                return False
            async with generation_gate:
                sent = await guarded_send([frame], guard)
        else:
            sent = await guarded_send([frame], guard)
        return bool(checked and sent)
    # Non-WS adapters have no async output lock: cover their final authority
    # check and original write with the same native generation gate.
    if generation_gate is not None:
        async with generation_gate:
            return bool(await asyncio.to_thread(lambda: current() and transport.write(frame)))
    return bool(await asyncio.to_thread(lambda: current() and transport.write(frame)))


def deliver_on_owner_loop(
    transport, loop: asyncio.AbstractEventLoop, frame: dict,
    current: Callable[[], bool],
    current_on_loop: Callable[[], bool] | None = None,
    generation_gate: asyncio.Lock | None = None,
) -> bool:
    """No session fanout or replacement viewer lookup."""
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is loop:
        raise GatewayScopeDeliveryError("scoped publish requires a worker thread")
    future = asyncio.run_coroutine_threadsafe(
        _send_on_owner_loop(transport, frame, current, current_on_loop, generation_gate), loop,
    )
    return bool(future.result())


def deliver_legacy(
    transport, frame: dict, current: Callable[[], bool],
) -> bool:
    """Pinned legacy peer: WS uses its owner loop; stdio writes synchronously."""
    loop = getattr(transport, "_loop", None)
    if loop is not None:
        return deliver_on_owner_loop(transport, loop, frame, current)
    guarded_write = getattr(transport, "write_if_current", None)
    if callable(guarded_write):
        return bool(guarded_write(frame, current))
    return bool(current() and transport.write(frame))
