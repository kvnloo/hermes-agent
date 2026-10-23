"""Live JSON-RPC plugin requests through the production TUI gateway (#636)."""

from __future__ import annotations

import queue
import threading
from functools import partial
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from hermes_cli import plugins


NAME = "hermes-tern.browser.blocks"


class Peer:
    def __init__(self):
        self.frames = queue.Queue()
        self.closed = False

    def write(self, frame):
        if self.closed:
            return False
        self.frames.put(frame)
        return True

    def close(self):
        self.closed = True

    def receive(self):
        return self.frames.get(timeout=5)


class StrictParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    value: int


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from tui_gateway import server

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(server, "_hermes_home", home)
    monkeypatch.setattr(server, "_sessions", {})
    plugins._reset_plugin_managers_for_tests()
    # This suite registers through PluginContext; a separate real-loader fixture tests
    # discovery, failure rollback and forced re-discovery.
    monkeypatch.setattr(plugins, "discover_plugins", lambda force=False: None)
    manager = plugins.get_plugin_manager()
    yield server, plugins, manager
    plugins._reset_plugin_managers_for_tests()


def install(plugins, manager, handler, schema=None):
    ctx = plugins.PluginContext(plugins.PluginManifest(name="hermes-tern"), manager)
    return ctx.register_gateway_method(NAME, handler, schema=schema)


def attach(server, sid, transport, *, profile_home=None):
    server._sessions[sid] = {
        "transport": transport, "profile_home": profile_home, "session_key": sid,
        "history": [], "history_lock": threading.Lock(), "running": False,
    }


def call(server, transport, method, rid=1, **params):
    response = server.dispatch({"jsonrpc": "2.0", "id": rid, "method": method, "params": params}, transport)
    return transport.receive() if response is None else response


def test_reject_async_callable_objects_and_generators(runtime):
    """Only synchronous callbacks may enter the profile's gateway method registry."""
    _, _, manager = runtime

    class AsyncCallable:
        async def __call__(self, request, params):
            return {"unexpected": True}

    class AsyncGeneratorCallable:
        async def __call__(self, request, params):
            yield {"unexpected": True}

    async def async_generator(request, params):
        yield {"unexpected": True}

    for handler in (AsyncCallable(), AsyncGeneratorCallable(), async_generator,
                    partial(AsyncCallable()), partial(AsyncGeneratorCallable())):
        with pytest.raises(TypeError, match="synchronous"):
            install(plugins, manager, handler)
    assert not manager._gateway_methods


def test_registered_method_capability_and_unload(runtime):
    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    # A sessionless capability probe must never disclose plugin registrations.
    assert server.handle_request({"id": 1, "method": "gateway.capabilities",
                                  "params": {}})["result"]["plugin_methods"] == []
    handle = install(
        plugins, manager,
        lambda request, params: {"profile": request.profile, "session": request.session_id,
                                 "value": params["value"]},
        schema=StrictParams,
    )
    found = call(server, peer, "gateway.capabilities", rid=2, session_id="owned")
    assert found["result"]["plugin_methods"] == [NAME]
    assert found["result"]["per_session_exclusive_submit"] in (True, False)
    reply = call(server, peer, NAME, rid=3, session_id="owned", value=7)
    assert reply["id"] == 3
    assert reply["result"] == {"profile": "default", "session": "owned", "value": 7}
    assert manager.unload("hermes-tern")
    assert not handle.active
    assert call(server, peer, "gateway.capabilities", rid=4,
                session_id="owned")["result"]["plugin_methods"] == []
    assert call(server, peer, NAME, rid=5, session_id="owned",
                value=7)["error"]["code"] == -32601
    install(plugins, manager, lambda request, params: {"reloaded": True})
    assert call(server, peer, NAME, rid=6, session_id="owned")["result"] == {"reloaded": True}


def test_namespace_profile_selection_and_detached_sessions_fail(runtime):
    server, plugins, manager = runtime
    primary, foreign = Peer(), Peer()
    attach(server, "alice", primary)
    attach(server, "bob", foreign)
    install(plugins, manager, lambda request, params: {"ok": True})
    assert call(server, primary, NAME, session_id="bob")["error"]["code"] == 4001
    assert call(server, primary, "gateway.capabilities", session_id="bob")["error"]["code"] == 4001
    assert call(server, primary, NAME, session_id="alice", profile="other")["error"]["code"] == 4001
    assert call(server, primary, NAME, session_id="missing")["error"]["code"] == 4001
    server._sessions["alice"]["transport"] = server._detached_ws_transport
    assert call(server, primary, NAME, session_id="alice")["error"]["code"] == 4001
    assert call(server, primary, "gateway.capabilities", session_id="alice")["error"]["code"] == 4001


def test_schema_failures_and_errors_do_not_crash_dispatch(runtime):
    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    install(plugins, manager, lambda request, params: {"n": params["value"]}, StrictParams)
    bad = call(server, peer, NAME, session_id="owned", value="seven")
    assert bad["error"]["code"] == -32602
    bad = call(server, peer, NAME, session_id="owned", value=2, bogus=True)
    assert bad["error"]["code"] == -32602
    assert call(server, peer, NAME, session_id="owned", value=2)["result"] == {"n": 2}
    manager.unload("hermes-tern")

    def broken(request, params):
        raise RuntimeError("sensitive token should not leave the gateway")

    install(plugins, manager, broken)
    error = call(server, peer, NAME, session_id="owned")
    assert error["error"]["code"] == -32000
    assert "sensitive token" not in str(error)
    manager.unload("hermes-tern")
    install(plugins, manager, lambda request, params: {"bad": object()})
    assert call(server, peer, NAME, session_id="owned")["error"]["code"] == -32000
    assert call(server, peer, "gateway.capabilities", session_id="owned")["result"]["plugin_methods"] == [NAME]


def test_concurrent_rpc_preserves_both_transports(runtime):
    server, plugins, manager = runtime
    first, second = Peer(), Peer()
    attach(server, "first", first)
    attach(server, "second", second)
    entered = threading.Event()
    release = threading.Event()

    def handler(request, params):
        request.assert_attached()
        if request.session_id == "first":
            entered.set()
            assert release.wait(5)
        from tui_gateway.transport import current_transport
        return {"sid": request.session_id, "peer": current_transport() is
                (first if request.session_id == "first" else second)}

    install(plugins, manager, handler)
    assert server.dispatch({"id": 11, "method": NAME,
                            "params": {"session_id": "first"}}, first) is None
    try:
        assert entered.wait(5)
        assert call(server, second, NAME, rid=12, session_id="second")["result"] == {
            "sid": "second", "peer": True}
    finally:
        release.set()
    assert first.receive()["result"] == {"sid": "first", "peer": True}


def test_detach_and_reuse_during_queued_work_rejected(runtime):
    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    entered = threading.Event()
    release = threading.Event()

    def handler(request, params):
        entered.set()
        assert release.wait(5)
        request.assert_attached()
        return {"ok": True}

    install(plugins, manager, handler)
    assert server.dispatch({"id": 42, "method": NAME,
                            "params": {"session_id": "owned"}}, peer) is None
    try:
        assert entered.wait(5)
        # Reusing a public session id (even with the same transport) cannot
        # authorize a worker holding the old record's generation.
        attach(server, "owned", peer)
    finally:
        release.set()
    assert peer.receive()["error"]["code"] == 4001


def test_capabilities_only_describe_callers_profile(runtime, tmp_path, monkeypatch):
    server, plugins, main = runtime
    first, second = Peer(), Peer()
    attach(server, "one", first)
    profile_home = tmp_path / ".hermes" / "profiles" / "work"
    profile_home.mkdir(parents=True)
    (profile_home / "config.yaml").write_text("{}\n", encoding="utf-8")
    attach(server, "two", second, profile_home=str(profile_home))
    install(plugins, main, lambda request, params: {"from": "default"})
    from hermes_constants import set_hermes_home_override, reset_hermes_home_override

    token = set_hermes_home_override(profile_home)
    try:
        secondary = plugins.get_plugin_manager()
        assert secondary is not main
        secondary_name = "work-plugin.browser.blocks"
        plugins.PluginContext(
            plugins.PluginManifest(name="work-plugin"), secondary,
        ).register_gateway_method(secondary_name, lambda request, params: {"from": "work"})
    finally:
        reset_hermes_home_override(token)
    assert call(server, first, "gateway.capabilities",
                session_id="one")["result"]["plugin_methods"] == [NAME]
    assert call(server, second, "gateway.capabilities",
                session_id="two")["result"]["plugin_methods"] == [secondary_name]
    assert call(server, first, secondary_name, session_id="one")["error"]["code"] == -32601
    assert call(server, first, secondary_name, session_id="two")["error"]["code"] == 4001
    assert call(server, second, secondary_name, session_id="two")["result"] == {"from": "work"}


def test_real_fixture_plugin_discoverable_and_callable_over_dispatch(runtime, tmp_path, monkeypatch):
    """No injected dispatcher functions: load actual fixture via PluginManager discovery."""
    import hermes_yaml as yaml

    server, plugins, manager = runtime
    home = tmp_path / ".hermes"
    plugin_dir = home / "plugins" / "hermes-tern"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        yaml.safe_dump({"name": "hermes-tern", "version": "1.0.0", "description": "gateway fixture"}),
        encoding="utf-8",
    )
    (plugin_dir / "__init__.py").write_text(
        "def handle(request, params):\n"
        "    request.assert_attached()\n"
        "    return {'profile': request.profile, 'session': request.session_id}\n"
        "def register(ctx):\n"
        "    ctx.register_gateway_method('hermes-tern.browser.blocks', handle)\n",
        encoding="utf-8",
    )
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": ["hermes-tern"]}}), encoding="utf-8",
    )
    monkeypatch.setattr(plugins, "get_bundled_plugins_dir", lambda: tmp_path / "empty-bundled")
    monkeypatch.setattr(plugins.PluginManager, "_scan_entry_points", lambda self: [])
    manager.discover_and_load()
    assert manager._plugins["hermes-tern"].enabled
    peer = Peer()
    attach(server, "real", peer)
    assert call(server, peer, "gateway.capabilities", session_id="real")["result"]["plugin_methods"] == [NAME]
    assert call(server, peer, NAME, session_id="real")["result"] == {
        "profile": "default", "session": "real",
    }
    manager.unload("hermes-tern")
    assert call(server, peer, NAME, session_id="real")["error"]["code"] == -32601


@pytest.mark.parametrize("name", [
    "mcp.servers.list", "mcp.servers.status", "pet.info.meta",
    "session.foreign.list", "vault.source.set",
])
def test_dotted_registered_core_methods_keep_normal_dispatch(runtime, monkeypatch, name):
    """#636 P1: dots alone never turn a registered core verb into a plugin RPC."""
    server, _, _ = runtime
    peer = Peer()
    assert name in server._methods
    observed = []
    production_handler = server._methods[name]

    def core(rid, params):
        observed.append(dict(params))
        return production_handler(rid, params)

    monkeypatch.setitem(server._methods, name, core)
    # The actual handler still runs: do not fake a result that would violate
    # the typed core contract in HERMES_TEST_ISOLATION=1.
    result = call(server, peer, name, profile="default")
    assert result["id"] == 1
    assert observed == [{"profile": "default"}]


def test_actual_sessionless_and_session_dotted_core_dispatch(runtime):
    """Call the production handlers through dispatch, not handle_request or a shape predicate."""
    server, _, _ = runtime
    peer = Peer()
    sessionless = call(server, peer, "session.foreign.list")
    assert sessionless["id"] == 1
    assert sessionless.get("error", {}).get("code") not in {4001, -32601}, sessionless

    attach(server, "core", peer)
    attached = call(server, peer, "session.events.since", rid=2,
                    session_id="core", last_seen=0)
    assert attached["id"] == 2
    assert "result" in attached, attached



def test_legacy_scope_post_return_progress_complete_original_transport_only(runtime):
    """Actual legacy JSON-RPC dispatcher and original peer transport."""
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    server, plugins, manager = runtime
    first, other = Peer(), Peer()
    attach(server, "owned", first)
    attach(server, "different", other)
    captured = []

    def handler(ctx, params):
        captured.append((ctx.capture_scope(), ctx))
        return {"accepted": True}

    install(plugins, manager, handler)
    assert call(server, first, NAME, session_id="owned")["result"] == {"accepted": True}
    lease, request = captured[0]
    with pytest.raises(PermissionError):
        request.capture_scope()
    assert lease.publish("hermes-tern.btw.progress", {"count": 1})
    assert lease.publish("hermes-tern.btw.complete", {"done": True})
    frames = [first.receive(), first.receive()]
    assert [f["params"]["payload"]["event_name"] for f in frames] == [
        "hermes-tern.btw.progress", "hermes-tern.btw.complete",
    ]
    assert frames[0]["params"]["type"] == "plugin.event"
    assert frames[0]["params"]["payload"] == {
        "plugin": "hermes-tern", "event_name": "hermes-tern.btw.progress",
        "profile": "default", "data": {"count": 1},
    }
    assert other.frames.empty()
    lease.close()
    lease.close()
    assert lease.cancellation.is_set()
    with pytest.raises(GatewayScopeError):
        lease.assert_current()


def test_legacy_scope_rejects_spoofing_and_revokes_after_reuse_or_unload(runtime):
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    leases = []
    install(plugins, manager, lambda ctx, params: leases.append(ctx.capture_scope()) or {"ok": True})
    assert call(server, peer, NAME, session_id="owned")["result"] == {"ok": True}
    lease = leases[-1]
    for name in ("session.info", "message.complete", "other.surface.update",
                 "hermes-tern.btw.Update"):
        with pytest.raises(GatewayScopeError):
            lease.publish(name, {})
    for invalid in ([], None, {"nested": {"set": {1, 2}}}, {"value": float("inf")}):
        with pytest.raises(GatewayScopeError):
            lease.publish("hermes-tern.btw.update", invalid)
    assert peer.frames.empty()

    attach(server, "owned", peer)  # same public ID and same peer, new live record
    with pytest.raises(GatewayScopeError):
        lease.assert_current()
    assert call(server, peer, NAME, session_id="owned")["result"] == {"ok": True}
    replacement = leases[-1]
    manager.unload("hermes-tern")
    install(plugins, manager, lambda ctx, params: {"new": True})
    with pytest.raises(GatewayScopeError):
        replacement.assert_current()
    assert peer.frames.empty()


def test_legacy_scope_fails_on_original_peer_loss_and_failed_rpc(runtime):
    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError, GatewayScopeError

    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    leases = []
    install(plugins, manager, lambda ctx, params: leases.append(ctx.capture_scope()) or {"ok": True})
    assert call(server, peer, NAME, session_id="owned")["result"] == {"ok": True}
    # Transport admission can fail without a closed flag; this is an
    # observable send failure, never a swallowed queued notification.
    peer.write = lambda _frame: False
    with pytest.raises(GatewayScopeDeliveryError):
        leases[-1].publish("hermes-tern.btw.update", {"v": 1})
    peer.close()
    with pytest.raises(GatewayScopeError):
        leases[-1].assert_current()

    manager.unload("hermes-tern")
    second = Peer()
    attach(server, "owned", second)

    def failing(ctx, params):
        leases.append(ctx.capture_scope())
        raise RuntimeError("do not disclose private value")

    install(plugins, manager, failing)
    reply = call(server, second, NAME, session_id="owned")
    assert reply["error"]["code"] == -32000
    assert "private value" not in str(reply)
    assert leases[-1].cancellation.is_set()
    with pytest.raises(GatewayScopeError):
        leases[-1].assert_current()


def test_legacy_scope_registration_capture_only_during_handler(runtime):
    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    stored = []

    def handler(ctx, params):
        stored.append(ctx)
        return {"ok": True}

    install(plugins, manager, handler)
    assert call(server, peer, NAME, session_id="owned")["result"] == {"ok": True}
    with pytest.raises(PermissionError, match="active registered handler"):
        stored[0].capture_scope()
    assert peer.frames.empty()



def test_legacy_scope_revoked_by_backend_retirement(runtime, monkeypatch):
    """Registered legacy lease cannot publish after its backend closes admission."""
    from hermes_cli.backend_retirement import retirement
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    server, plugins, manager = runtime
    peer = Peer()
    attach(server, "owned", peer)
    captured = []
    install(plugins, manager, lambda ctx, params: captured.append(ctx.capture_scope()) or {"ok": True})
    assert call(server, peer, NAME, session_id="owned")["result"] == {"ok": True}
    lease = captured[-1]
    monkeypatch.setattr(retirement, "acquire", lambda: False)
    with pytest.raises(GatewayScopeError):
        lease.publish("hermes-tern.btw.complete", {"done": True})
    assert lease.cancellation.is_set()
    assert peer.frames.empty()


@pytest.mark.parametrize("revocation", ["detach", "reuse", "unload"])
def test_legacy_scope_real_stdio_output_lock_fences_queued_publication(runtime, monkeypatch, revocation):
    """Registered legacy dispatch + real StdioTransport, never a fake delivery callback."""
    import json

    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError
    from tui_gateway.transport import StdioTransport

    class FrameStream:
        def __init__(self):
            self.frames = queue.Queue()

        def write(self, line):
            self.frames.put(json.loads(line))
            return len(line)

        def flush(self):
            pass

    server, plugins, manager = runtime
    stream, lock = FrameStream(), threading.Lock()
    stdio = StdioTransport(lambda: stream, lock)
    attach(server, "owned", stdio)
    scopes = []
    install(plugins, manager, lambda ctx, params: scopes.append(ctx.capture_scope()) or {"accepted": True})

    # Exercise the registered legacy dispatcher and consume its actual stdio RPC reply.
    assert server.dispatch({"id": 42, "method": NAME, "params": {"session_id": "owned"}}, stdio) is None
    assert stream.frames.get(timeout=5)["result"] == {"accepted": True}
    lease = scopes[-1]

    entered = threading.Event()
    original_guarded_write = StdioTransport.write_if_current

    def observed_guarded_write(self, frame, current):
        entered.set()
        return original_guarded_write(self, frame, current)

    monkeypatch.setattr(StdioTransport, "write_if_current", observed_guarded_write)
    outcomes = queue.Queue()
    lock.acquire()
    try:
        def publish():
            try:
                outcomes.put(lease.publish("hermes-tern.btw.complete", {"done": True}))
            except Exception as exc:
                outcomes.put(exc)

        worker = threading.Thread(target=publish, daemon=True)
        worker.start()
        assert entered.wait(5), "publisher never reached real stdio output lock"
        assert outcomes.empty()  # queued behind the true output lock
        if revocation == "detach":
            server._sessions.pop("owned")
        elif revocation == "reuse":
            attach(server, "owned", stdio)  # identical ID and peer, different live record
        else:
            manager.unload("hermes-tern")  # original registration is retired
    finally:
        lock.release()

    worker.join(5)
    assert not worker.is_alive()
    assert isinstance(outcomes.get_nowait(), GatewayScopeDeliveryError)
    assert stream.frames.empty()  # no escaped plugin.event after revocation
    assert lease.cancellation.is_set()


def test_legacy_scope_real_stdio_accepts_large_deep_finite_json(runtime):
    """Use the same JSON serializer/output lock as ordinary legacy gateway frames."""
    import json

    from tui_gateway.transport import StdioTransport

    class FrameStream:
        def __init__(self):
            self.frames = queue.Queue()

        def write(self, line):
            self.frames.put(json.loads(line))
            return len(line)

        def flush(self):
            pass

    server, plugins, manager = runtime
    stream = FrameStream()
    stdio = StdioTransport(lambda: stream, threading.Lock())
    attach(server, "owned", stdio)
    leases = []
    install(plugins, manager, lambda ctx, params: leases.append(ctx.capture_scope()) or {"accepted": True})
    assert server.dispatch({"id": 42, "method": NAME, "params": {"session_id": "owned"}}, stdio) is None
    assert stream.frames.get(timeout=5)["result"] == {"accepted": True}

    nested = {"leaf": True}
    for _ in range(72):
        nested = {"child": nested}
    payload = {"body": "x" * (300 * 1024), "deep": nested}
    assert leases[-1].publish("hermes-tern.btw.complete", payload)
    frame = stream.frames.get(timeout=5)
    assert frame["params"]["type"] == "plugin.event"
    assert frame["params"]["payload"]["data"] == payload


@pytest.mark.parametrize("outcome", ["delivered", "unloaded"])
@pytest.mark.asyncio
async def test_legacy_scope_owner_loop_rejects_during_real_ws_send(runtime, outcome):
    """Legacy dispatch must carry the original WSTransport loop into captured scopes."""
    import asyncio
    import json

    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError, GatewayScopeError
    from tests.waiting import async_wait_until
    from tui_gateway.ws import WSTransport

    class Socket:
        def __init__(self):
            self.frames = []

        async def send_text(self, line):
            self.frames.append(json.loads(line))

    server, plugins, manager = runtime
    socket = Socket()
    transport = WSTransport(socket, asyncio.get_running_loop())
    queued = asyncio.Event()
    original_send = transport.write_many_if_current_async

    async def observed_send(frames, guard):
        queued.set()
        return await original_send(frames, guard)

    transport.write_many_if_current_async = observed_send
    attach(server, "owned", transport)
    leases, contexts = [], []

    def handler(request, params):
        contexts.append(request)
        leases.append(request.capture_scope())
        return {"ok": True}

    install(plugins, manager, handler)
    assert server.dispatch({"id": 42, "method": NAME, "params": {"session_id": "owned"}}, transport) is None
    await async_wait_until(lambda: len(socket.frames) == 1, timeout=5, what="legacy WS RPC reply")
    assert socket.frames[0]["result"] == {"ok": True}
    lease = leases[-1]

    async with transport._send_lock:
        publishing = asyncio.create_task(asyncio.to_thread(
            lease.publish, "hermes-tern.btw.complete", {"done": True},
        ))
        await asyncio.wait_for(queued.wait(), timeout=5)
        with pytest.raises(GatewayScopeError, match="asyncio.to_thread"):
            lease.publish("hermes-tern.btw.update", {"count": 2})
        with pytest.raises(GatewayScopeError, match="asyncio.to_thread"):
            lease.close()
        with pytest.raises(GatewayScopeError, match="asyncio.to_thread"):
            lease.assert_current()
        with pytest.raises(RuntimeError, match="asyncio.to_thread"):
            contexts[-1].assert_attached()
        assert not lease.cancellation.is_set()
        if outcome == "unloaded":
            manager.unload("hermes-tern")

    if outcome == "delivered":
        assert await asyncio.wait_for(publishing, timeout=5)
        assert len(socket.frames) == 2
        assert socket.frames[1]["params"]["payload"]["event_name"] == "hermes-tern.btw.complete"
    else:
        with pytest.raises(GatewayScopeDeliveryError):
            await asyncio.wait_for(publishing, timeout=5)
        assert len(socket.frames) == 1
    await asyncio.to_thread(lease.close)
    assert lease.cancellation.is_set()
    with pytest.raises(GatewayScopeError):
        await asyncio.to_thread(lease.assert_current)
