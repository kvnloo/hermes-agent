"""Canonical hermes-gateway-v1 plugin RPCs through the native authority connection (#636).

These requests go through the production WS connection factory and router, not a
second test dispatcher or the legacy TUI session table.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from hermes_cli import plugins

from gateway.session_authority import LiveSession, SessionAuthority
from hermes_state import SessionDB
from hermes_state_runtime import begin_runtime_epoch
from tests.waiting import async_wait_until
from tui_gateway.ws import _authority_connection, _dispatch_request


NAME = "hermes-tern.surface.echo"
BETA_NAME = "beta-plugin.surface.echo"


class Transport:
    def __init__(self):
        self.closed = False
        self.frames = []

    def write(self, frame):
        if self.closed:
            return False
        self.frames.append(frame)
        return True


@pytest.fixture
def native(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    plugins._reset_plugin_managers_for_tests()
    monkeypatch.setattr(plugins, "discover_plugins", lambda force=False: None)
    manager = plugins.get_plugin_manager()
    db = SessionDB(db_path=home / "state.db")
    db.create_session("owned", source="test")
    db.create_session("foreign", source="test")
    runner = SimpleNamespace(_draining=False, config=SimpleNamespace(multiplex_profiles=False))
    authority = SessionAuthority(runner, profile_id=str(home), instance_id="instance",
                                 db=db, epoch=begin_runtime_epoch(db, instance_id="instance"))
    authority.sessions["owned"] = LiveSession(None, "route-owned")
    authority.sessions["foreign"] = LiveSession(None, "route-foreign")
    yield SimpleNamespace(home=home, manager=manager, plugins=plugins,
                          db=db, runner=runner, authority=authority)
    db.close()
    plugins._reset_plugin_managers_for_tests()


def connect(authority, *, subject="human", capabilities=None, transport=None, operator=True):
    """Exercise the actual WS's authority connection selection from its authenticated scope."""
    identity = {"user_id": subject, "provider": "local", "native_bootstrap": True,
                "profile_id": authority.profile_id, "instance_id": authority.instance_id}
    if capabilities is not None:
        identity["capabilities"] = capabilities
    return _authority_connection(
        SimpleNamespace(scope={"hermes.session_authority": authority}),
        transport or Transport(), identity, operator=operator,
    )


async def request(connection, method, params=None, rid=1):
    frame = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
    return await _dispatch_request(connection, frame, method, connection.transport)


async def resume(connection, sid="owned"):
    reply = await request(connection, "session.resume", {"session_id": sid})
    assert "result" in reply, reply
    return reply["result"]["subscription_id"]


def install(native, handler, *, name=NAME, schema=None):
    ctx = native.plugins.PluginContext(native.plugins.PluginManifest(name=name.split(".")[0]), native.manager)
    return ctx.register_gateway_method(name, handler, schema=schema)


@pytest.mark.asyncio
async def test_default_native_client_discovers_and_calls_real_fixture_plugin(native, tmp_path, monkeypatch):
    """Default hermes tern bootstrap's canonical path: real plugin discovery + attached RPC."""
    import hermes_yaml as yaml

    home = native.home
    plugin_dir = home / "plugins" / "hermes-tern"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        yaml.safe_dump({"name": "hermes-tern", "version": "1.0.0",
                        "description": "canonical method fixture"}), encoding="utf-8")
    (plugin_dir / "__init__.py").write_text(
        "import threading\n"
        "from pydantic import BaseModel, ConfigDict\n"
        "class EchoParams(BaseModel):\n"
        "    model_config = ConfigDict(extra='forbid')\n"
        "    session_id: str\n"
        "    value: int\n"
        "def echo(request, params):\n"
        "    request.assert_attached()\n"
        "    return {'profile': request.profile, 'session': request.session_id,\n"
        "            'value': params['value'], 'worker': threading.get_ident()}\n"
        "def register(ctx):\n"
        "    ctx.register_gateway_method('hermes-tern.surface.echo', echo, schema=EchoParams)\n",
        encoding="utf-8",
    )
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": ["hermes-tern"]}}), encoding="utf-8")
    monkeypatch.setattr(native.plugins, "get_bundled_plugins_dir", lambda: tmp_path / "empty-bundled")
    monkeypatch.setattr(native.plugins.PluginManager, "_scan_entry_points", lambda self: [])
    native.manager.discover_and_load()
    assert native.manager._plugins["hermes-tern"].enabled

    viewer = connect(native.authority)
    try:
        # No attached session, even if the caller names a profile, gives no inventory.
        sessionless = await request(viewer, "gateway.capabilities")
        assert sessionless["result"]["plugin_methods"] == []
        denied = await request(viewer, NAME, {"session_id": "owned", "value": 2})
        assert denied["error"]["code"] == 4001

        await resume(viewer)
        assert (await request(viewer, "ping"))["result"] == {"pong": True}
        assert (await request(viewer, "gateway.capabilities", {"session_id": "owned"}))["result"]["plugin_methods"] == [NAME]
        result = await request(viewer, NAME, {"session_id": "owned", "value": 7})
        assert result["result"]["profile"] == "default", result
        assert result["result"]["session"] == "owned"
        assert result["result"]["value"] == 7
        assert result["result"]["worker"] != threading.get_ident()
        bad = await request(viewer, NAME, {"session_id": "owned", "value": "seven"})
        assert bad["error"]["code"] == -32602
        assert (await request(viewer, NAME, {"session_id": "owned", "value": 7, "extra": 1}))["error"]["code"] == -32602
        assert (await request(viewer, NAME, {
            "session_id": "owned", "value": 7, "profile": "default",
        }))["error"]["code"] == 4001

        assert native.manager.unload("hermes-tern")
        assert (await request(viewer, "gateway.capabilities", {
            "session_id": "owned"}))["result"]["plugin_methods"] == []
        assert (await request(viewer, NAME, {
            "session_id": "owned", "value": 7}))["error"]["code"] == -32601
        assert (await request(viewer, "ping"))["result"] == {"pong": True}
    finally:
        await viewer.close()


@pytest.mark.asyncio
async def test_canonical_readonly_foreign_session_and_profile_are_denied(native):
    observed = []
    install(native, lambda ctx, params: observed.append(ctx.session_id) or {"changed": True})
    first = connect(native.authority)
    other = connect(native.authority, subject="other")
    read_only = connect(native.authority, subject="reader", capabilities=["session:read"])
    try:
        await resume(first)
        await resume(other, "foreign")
        await resume(read_only)
        for viewer, params in (
            (first, {"session_id": "foreign"}),
            (first, {"session_id": "owned", "profile": "beta"}),
            (other, {"session_id": "owned"}),
            (read_only, {"session_id": "owned"}),
        ):
            refused = await request(viewer, NAME, params)
            assert refused["error"]["code"] == 4001, refused
        assert (await request(read_only, "gateway.capabilities", {
            "session_id": "owned"}))["error"]["code"] == 4001
        assert (await request(first, "gateway.capabilities", {
            "session_id": "foreign"}))["error"]["code"] == 4001
        assert observed == []
    finally:
        for viewer in (first, other, read_only):
            await viewer.close()


@pytest.mark.asyncio
async def test_canonical_detach_reattach_and_reused_session_cannot_resurrect_queued_work(native):
    entered, release = threading.Event(), threading.Event()

    def slow(ctx, params):
        entered.set()
        assert release.wait(10), "test failed to release plugin worker"
        ctx.assert_attached()
        return {"wrote": True}

    install(native, slow)
    viewer = connect(native.authority)
    peer = connect(native.authority, subject="peer")
    try:
        token = await resume(viewer)
        await resume(peer)
        pending = asyncio.create_task(request(viewer, NAME, {"session_id": "owned"}))
        try:
            await async_wait_until(entered.is_set, timeout=10, what="native plugin worker entry")
            detached = await request(viewer, "session.detach", {
                "session_id": "owned", "subscription_id": token,
            })
            assert detached["result"]["detached"] is True
            await resume(viewer)  # same public id on the same transport is NOT the previous lease
        finally:
            release.set()
        assert (await pending)["error"]["code"] == 4001

        # Same public sid but a different live slot must not reauthorize a captured handler.
        entered.clear()
        release.clear()
        pending = asyncio.create_task(request(viewer, NAME, {"session_id": "owned"}))
        try:
            await async_wait_until(entered.is_set, timeout=10, what="native reused-session worker")
            native.authority.sessions["owned"] = LiveSession(None, "reused")
        finally:
            release.set()
        assert (await pending)["error"]["code"] == 4001
    finally:
        await viewer.close()
        await peer.close()


@pytest.mark.asyncio
async def test_canonical_disconnect_retirement_and_secret_safe_failures(native):
    install(native, lambda ctx, params: (_ for _ in ()).throw(
        RuntimeError("private-secret-value")))
    viewer = connect(native.authority)
    try:
        await resume(viewer)
        error = await request(viewer, NAME, {"session_id": "owned"})
        assert error["error"]["code"] == -32000
        assert "private-secret-value" not in str(error)
        native.authority.retiring = True
        assert (await request(viewer, NAME, {"session_id": "owned"}))["error"]["code"] == 4001
        native.authority.retiring = False
    finally:
        await viewer.close()
    disconnected = await request(viewer, NAME, {"session_id": "owned"})
    assert disconnected["error"]["code"] == 4001


@pytest.mark.asyncio
async def test_canonical_same_name_isolated_by_owner_profile(native):
    from gateway.run import _profile_runtime_scope

    beta = native.home / "profiles" / "beta"
    beta.mkdir(parents=True)
    (beta / "config.yaml").write_text("{}\n", encoding="utf-8")
    second_db = SessionDB(db_path=beta / "state.db")
    second_db.create_session("beta-sid", source="test")
    second = SessionAuthority(native.runner, profile_id=str(beta), instance_id="instance",
                              db=second_db, epoch=begin_runtime_epoch(second_db, instance_id="instance"))
    second.sessions["beta-sid"] = LiveSession(None, "beta-route")
    first_view = connect(native.authority)
    second_view = connect(second)
    try:
        native.runner.config.multiplex_profiles = True
        install(native, lambda ctx, params: {"profile": ctx.profile})
        with _profile_runtime_scope(beta):
            beta_manager = native.plugins.get_plugin_manager()
            assert beta_manager is not native.manager
            beta_ctx = native.plugins.PluginContext(
                native.plugins.PluginManifest(name="beta-plugin"), beta_manager)
            beta_ctx.register_gateway_method(BETA_NAME, lambda ctx, params: {"profile": ctx.profile})
        await resume(first_view)
        await resume(second_view, "beta-sid")
        a = await request(first_view, "gateway.capabilities", {"session_id": "owned"})
        b = await request(second_view, "gateway.capabilities", {"session_id": "beta-sid"})
        assert a["result"]["plugin_methods"] == [NAME]
        assert b["result"]["plugin_methods"] == [BETA_NAME]
        assert (await request(first_view, BETA_NAME, {"session_id": "owned"}))["error"]["code"] == -32601
        assert (await request(second_view, NAME, {"session_id": "beta-sid"}))["error"]["code"] == -32601
        assert (await request(second_view, BETA_NAME, {"session_id": "beta-sid"}))["result"] == {
            "profile": "beta"}
    finally:
        await first_view.close()
        await second_view.close()
        second_db.close()


@pytest.mark.asyncio
async def test_canonical_execution_generation_change_revokes_inflight_method(native):
    """A live session reused for a later execution cannot accept an older callback."""
    entered, release = threading.Event(), threading.Event()

    def slow(ctx, params):
        entered.set()
        assert release.wait(10), "test failed to release plugin worker"
        ctx.assert_attached()
        return {"changed": True}

    install(native, slow)
    viewer = connect(native.authority)
    try:
        await resume(viewer)
        task = asyncio.create_task(request(viewer, NAME, {"session_id": "owned"}))
        try:
            await async_wait_until(entered.is_set, timeout=10, what="plugin generation admission")
            # Model a new live runtime generation in the same DB row while the
            # previously admitted handler is off-loop. The subscription did not move.
            native.db._execute_write(lambda conn: conn.execute(
                "UPDATE sessions SET runtime_generation=runtime_generation+1 WHERE id=?",
                ("owned",),
            ))
        finally:
            release.set()
        assert (await task)["error"]["code"] == 4001
    finally:
        await viewer.close()


@pytest.mark.asyncio
async def test_scope_publishes_post_return_progress_completion_to_original_native_viewer(native):
    """Actual AuthorityConnection/router/transport output, not a fake publish callback."""
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    captured = []

    def handler(request, params):
        captured.append((request.capture_scope(), request))
        return {"started": True}

    install(native, handler)
    viewer = connect(native.authority)
    second = connect(native.authority, subject="second")
    try:
        await resume(viewer)
        await resume(second)
        assert (await request(viewer, NAME, {"session_id": "owned"}))["result"] == {"started": True}
        lease, rpc_context = captured[0]
        with pytest.raises(PermissionError):
            await asyncio.to_thread(rpc_context.assert_attached)  # the RPC itself is not durable
        with pytest.raises(PermissionError):
            await asyncio.to_thread(rpc_context.capture_scope)  # no capture after handler return
        assert await asyncio.to_thread(lease.publish, "hermes-tern.btw.progress", {"count": 1})
        assert await asyncio.to_thread(lease.publish, "hermes-tern.btw.complete", {"done": True})
        assert [f["params"]["payload"]["event_name"] for f in viewer.transport.frames] == [
            "hermes-tern.btw.progress", "hermes-tern.btw.complete",
        ]
        assert second.transport.frames == []
        first = viewer.transport.frames[0]
        assert first["method"] == "event"
        assert first["params"]["type"] == "plugin.event"
        assert first["params"]["session_id"] == "owned"
        assert first["params"]["payload"] == {
            "plugin": "hermes-tern", "event_name": "hermes-tern.btw.progress",
            "profile": "default", "data": {"count": 1},
        }
        await asyncio.to_thread(lease.close)
        await asyncio.to_thread(lease.close)
        assert lease.cancellation.is_set()
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(lease.publish, "hermes-tern.btw.complete", {"done": True})
        assert len(viewer.transport.frames) == 2  # close cannot retract a sent final frame
    finally:
        await viewer.close()
        await second.close()


@pytest.mark.asyncio
async def test_scope_rejects_foreign_names_core_spoofing_and_malformed_payload(native):
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    leases = []
    install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
    viewer = connect(native.authority)
    try:
        await resume(viewer)
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        lease = leases[0]
        for name in ("message.complete", "gateway.ready", "other.btw.complete",
                     "hermes-tern..complete", "hermes-tern.btw.Complete"):
            with pytest.raises(GatewayScopeError, match="event name"):
                await asyncio.to_thread(lease.publish, name, {"v": 1})
        for payload in (None, [], {"v": float("nan")}, {"v": {1: "coerced"}},
                        {"v": object()}, {"v": (1, 2)}):
            with pytest.raises(GatewayScopeError, match="JSON"):
                await asyncio.to_thread(lease.publish, "hermes-tern.btw.update", payload)
        assert viewer.transport.frames == []
        assert await asyncio.to_thread(lease.publish, "hermes-tern.btw.complete", {})
    finally:
        await viewer.close()


@pytest.mark.asyncio
async def test_scope_loses_original_subscription_connection_and_registration(native):
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    leases = []
    install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
    viewer = connect(native.authority)
    peer = connect(native.authority, subject="peer")
    try:
        token = await resume(viewer)
        await resume(peer)
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        lease = leases[-1]
        assert (await request(viewer, "session.detach", {
            "session_id": "owned", "subscription_id": token,
        }))["result"]["detached"]
        await resume(viewer)
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(lease.assert_current)
        assert viewer.transport.frames == peer.transport.frames == []

        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        old = leases[-1]
        native.manager.unload("hermes-tern")
        install(native, lambda request, params: {"replacement": True})
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(old.assert_current)

        # Closing a connection revokes only its own remaining lease.
        native.manager.unload("hermes-tern")
        install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        owned = leases[-1]
        await viewer.close()
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(owned.assert_current)
        assert peer.transport.frames == []
    finally:
        await viewer.close()
        await peer.close()


@pytest.mark.asyncio
async def test_scope_epoch_and_persisted_runtime_generation_revoke_not_new_turn(native):
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    leases = []
    install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
    viewer = connect(native.authority)
    try:
        await resume(viewer)
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        lease = leases[-1]
        # A conversation turn is not a runtime lifetime change.
        assert await asyncio.to_thread(lease.publish, "hermes-tern.btw.update", {"turn": 2})
        native.authority.epoch += 1
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(lease.assert_current)
        native.authority.epoch -= 1

        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        lease = leases[-1]
        native.db._execute_write(lambda conn: conn.execute(
            "UPDATE sessions SET runtime_generation=runtime_generation+1 WHERE id=?",
            ("owned",),
        ))
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(lease.assert_current)
        assert len(viewer.transport.frames) == 1
    finally:
        await viewer.close()


@pytest.mark.asyncio
async def test_scope_failed_and_cancelled_rpc_never_leave_valid_publishers(native):
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    leases = []

    def failing(request, params):
        leases.append(request.capture_scope())
        raise RuntimeError("sensitive secret")

    install(native, failing)
    viewer = connect(native.authority)
    try:
        await resume(viewer)
        answer = await request(viewer, NAME, {"session_id": "owned"})
        assert answer["error"]["code"] == -32000
        assert "sensitive" not in str(answer)
        assert leases[-1].cancellation.is_set()
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(leases[-1].assert_current)
        native.manager.unload("hermes-tern")

        entered, release = threading.Event(), threading.Event()

        def cancelled(request, params):
            leases.append(request.capture_scope())
            entered.set()
            release.wait(10)
            return {"ok": True}

        install(native, cancelled)
        pending = asyncio.create_task(request(viewer, NAME, {"session_id": "owned"}))
        try:
            await async_wait_until(entered.is_set, timeout=10, what="captured cancellation scope")
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
        finally:
            release.set()
        assert leases[-1].cancellation.is_set()
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(leases[-1].assert_current)
        assert viewer.transport.frames == []
    finally:
        await viewer.close()


@pytest.mark.parametrize("revocation", ["detach", "reuse", "unload", "generation"])
@pytest.mark.asyncio
async def test_scope_queued_send_rechecks_at_original_ws_write_after_detach(native, revocation):
    """Use the real WSTransport send lock, not an event-publisher test double."""
    import json

    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError
    from tui_gateway.ws import WSTransport

    class BlockedSocket:
        def __init__(self):
            self.entered = asyncio.Event()
            self.release = asyncio.Event()
            self.frames = []

        async def send_text(self, line):
            self.entered.set()
            await self.release.wait()
            self.frames.append(json.loads(line))

    sock = BlockedSocket()
    transport = WSTransport(sock, asyncio.get_running_loop())
    queued = asyncio.Event()
    original_guarded_send = transport.write_many_if_current_async

    async def observed_guarded_send(frames, guard):
        queued.set()
        return await original_guarded_send(frames, guard)

    transport.write_many_if_current_async = observed_guarded_send
    leases = []
    install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
    viewer = connect(native.authority, transport=transport)
    try:
        token = await resume(viewer)
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        lease = leases[-1]
        blocking = asyncio.create_task(transport.write_async({"jsonrpc": "2.0", "id": 9, "result": {}}))
        await asyncio.wait_for(sock.entered.wait(), timeout=5)
        publishing = asyncio.create_task(asyncio.to_thread(
            lease.publish, "hermes-tern.btw.complete", {"done": True},
        ))
        try:
            # Observe scheduling inside the real transport, not a timing guess.
            await asyncio.wait_for(queued.wait(), timeout=5)
            if revocation in ("detach", "reuse"):
                assert (await request(viewer, "session.detach", {
                    "session_id": "owned", "subscription_id": token,
                }))["result"]["detached"]
                if revocation == "reuse":
                    # Same public ID and connection still cannot regain authority.
                    await resume(viewer)
            elif revocation == "unload":
                native.manager.unload("hermes-tern")
            else:
                native.db._execute_write(lambda conn: conn.execute(
                    "UPDATE sessions SET runtime_generation=runtime_generation+1 WHERE id=?",
                    ("owned",),
                ))
        finally:
            sock.release.set()
        assert await blocking
        with pytest.raises(GatewayScopeDeliveryError):
            await publishing
        assert not any(f.get("params", {}).get("type") == "plugin.event" for f in sock.frames)
        assert lease.cancellation.is_set()
    finally:
        await viewer.close()




@pytest.mark.parametrize("outcome", ["delivered", "unloaded"])
@pytest.mark.asyncio
async def test_scope_owner_loop_cannot_block_queued_real_ws_publication(native, monkeypatch, outcome):
    """A worker owns the lease lock while the real WS send lock is held on its owner loop."""
    import json

    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError, GatewayScopeError
    from tui_gateway.ws import WSTransport

    class Socket:
        def __init__(self):
            self.frames = []

        async def send_text(self, line):
            self.frames.append(json.loads(line))

    socket = Socket()
    loop = asyncio.get_running_loop()
    owner_thread = threading.get_ident()
    transport = WSTransport(socket, loop)
    queued = asyncio.Event()
    original_send = transport.write_many_if_current_async

    async def observed_send(frames, guard):
        queued.set()
        return await original_send(frames, guard)

    transport.write_many_if_current_async = observed_send
    leases, contexts = [], []

    def handler(request, params):
        contexts.append(request)
        leases.append(request.capture_scope())
        return {"ok": True}

    install(native, handler)
    viewer = connect(native.authority, transport=transport)
    original_get_session = native.db.get_session

    def checked_get_session(*args, **kwargs):
        assert threading.get_ident() != owner_thread, "authority DB read on WS owner loop"
        return original_get_session(*args, **kwargs)

    try:
        await resume(viewer)
        assert (await request(viewer, NAME, {"session_id": "owned"}))["result"] == {"ok": True}
        lease = leases[-1]
        monkeypatch.setattr(native.db, "get_session", checked_get_session)
        async with transport._send_lock:
            publishing = asyncio.create_task(asyncio.to_thread(
                lease.publish, "hermes-tern.btw.complete", {"done": True},
            ))
            # Reaching the real WS guard proves the worker is waiting under
            # _publish_lock for THIS loop to complete the actual guarded send.
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
                native.manager.unload("hermes-tern")
        if outcome == "delivered":
            assert await asyncio.wait_for(publishing, timeout=5)
            assert len(socket.frames) == 1
            assert socket.frames[0]["params"]["payload"]["event_name"] == "hermes-tern.btw.complete"
        else:
            with pytest.raises(GatewayScopeDeliveryError):
                await asyncio.wait_for(publishing, timeout=5)
            assert not socket.frames
        # A worker close retains synchronous drain/revoke semantics in both cases.
        await asyncio.to_thread(lease.close)
        await asyncio.to_thread(lease.close)
        assert lease.cancellation.is_set()
        with pytest.raises(GatewayScopeError):
            await asyncio.to_thread(lease.assert_current)
    finally:
        monkeypatch.setattr(native.db, "get_session", original_get_session)
        await viewer.close()


@pytest.mark.asyncio
async def test_scope_started_before_rpc_settles_only_publishes_after_success(native):
    """Background thread starts during sync handler, never emits provisional events."""
    from hermes_cli.plugin_gateway_scopes import GatewayScopeError

    entered, release = threading.Event(), threading.Event()
    workers = []
    outcome = []

    def handler(request, params):
        lease = request.capture_scope()
        settled_wait = lease._admission._settled.wait

        def require_rpc_settlement(timeout=None):
            # A scope has no independent 60-second deadline: cancellation or
            # handler completion is the only admission decision.
            assert timeout is None
            return settled_wait(timeout)

        lease._admission._settled.wait = require_rpc_settlement

        def worker():
            try:
                outcome.append(lease.publish("hermes-tern.btw.complete", {"done": True}))
            except GatewayScopeError:
                outcome.append(False)
            finally:
                lease.close()

        work = threading.Thread(target=worker, daemon=True)
        work.start()
        workers.append(work)
        entered.set()
        assert release.wait(10)
        if params.get("fail"):
            raise RuntimeError("private failure")
        return {"accepted": True}

    install(native, handler)
    viewer = connect(native.authority)
    try:
        await resume(viewer)
        first = asyncio.create_task(request(viewer, NAME, {"session_id": "owned"}))
        await async_wait_until(entered.is_set, timeout=10, what="pre-return publisher")
        assert viewer.transport.frames == []  # cannot send while admission is pending
        release.set()
        assert (await first)["result"] == {"accepted": True}
        await asyncio.to_thread(workers[-1].join, 5)
        assert outcome == [True]
        assert len(viewer.transport.frames) == 1

        entered.clear()
        release.clear()
        second = asyncio.create_task(request(viewer, NAME, {"session_id": "owned", "fail": True}))
        await async_wait_until(entered.is_set, timeout=10, what="failed pre-return publisher")
        assert len(viewer.transport.frames) == 1
        release.set()
        assert (await second)["error"]["code"] == -32000
        await asyncio.to_thread(workers[-1].join, 5)
        assert outcome == [True, False]
        assert len(viewer.transport.frames) == 1

        entered.clear()
        release.clear()
        cancelled = asyncio.create_task(request(viewer, NAME, {"session_id": "owned"}))
        await async_wait_until(entered.is_set, timeout=10, what="cancelled pre-return publisher")
        assert len(viewer.transport.frames) == 1
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        await asyncio.to_thread(workers[-1].join, 5)
        assert not workers[-1].is_alive()
        assert outcome == [True, False, False]
        assert len(viewer.transport.frames) == 1
    finally:
        release.set()
        await viewer.close()


@pytest.mark.parametrize("revocation", ["none", "detach", "unload", "generation"])
@pytest.mark.asyncio
async def test_scope_canonical_ws_token_accounting_never_blocks_owner_loop(native, monkeypatch, revocation):
    """Registered canonical RPC and real WS lock, even when get_session flushes slowly."""
    import json

    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError
    from tui_gateway.ws import WSTransport

    class Socket:
        def __init__(self):
            self.frames = []

        async def send_text(self, line):
            self.frames.append(json.loads(line))

    loop_thread = threading.get_ident()
    enabled, in_flush, finish_flush = threading.Event(), threading.Event(), threading.Event()
    flush_threads = []
    original_flush = native.db.flush_token_counts

    def slow_accounting(*args, **kwargs):
        if enabled.is_set():
            flush_threads.append(threading.get_ident())
            # First read is in the publishing worker; second is the
            # pre-admission check. The final generation read still executes
            # off-loop under the live writer gate and real WS output lock.
            if len(flush_threads) == 2 and threading.get_ident() != loop_thread:
                in_flush.set()
                assert finish_flush.wait(5), "release the simulated token-accounting writer"
        return original_flush(*args, **kwargs)

    monkeypatch.setattr(native.db, "flush_token_counts", slow_accounting)
    socket = Socket()
    transport = WSTransport(socket, asyncio.get_running_loop())
    leases = []
    install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
    viewer = connect(native.authority, transport=transport)
    try:
        token = await resume(viewer)
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        enabled.set()
        publishing = asyncio.create_task(asyncio.to_thread(
            leases[-1].publish, "hermes-tern.btw.complete", {"done": True},
        ))
        try:
            await async_wait_until(in_flush.is_set, timeout=5, what="off-loop token flush under WS send lock")
            # The owner loop must be able to service a real canonical core RPC
            # while the authoritative generation check waits on token accounting.
            assert (await asyncio.wait_for(request(viewer, "ping"), timeout=2))["result"] == {"pong": True}
            if revocation == "detach":
                assert (await request(viewer, "session.detach", {
                    "session_id": "owned", "subscription_id": token,
                }))["result"]["detached"]
            elif revocation == "unload":
                native.manager.unload("hermes-tern")
            elif revocation == "generation":
                native.db._execute_write(lambda conn: conn.execute(
                    "UPDATE sessions SET runtime_generation=runtime_generation+1 WHERE id=?",
                    ("owned",),
                ))
        finally:
            finish_flush.set()
        if revocation == "none":
            assert await asyncio.wait_for(publishing, timeout=5)
            assert len(socket.frames) == 1
            assert socket.frames[0]["params"]["payload"]["event_name"] == "hermes-tern.btw.complete"
        else:
            with pytest.raises(GatewayScopeDeliveryError):
                await asyncio.wait_for(publishing, timeout=5)
            assert not any(f.get("params", {}).get("type") == "plugin.event" for f in socket.frames)
        assert len(flush_threads) >= 2
        assert all(t != loop_thread for t in flush_threads[:2])
    finally:
        enabled.clear()
        finish_flush.set()
        await viewer.close()


@pytest.mark.asyncio
async def test_scope_canonical_ws_accepts_large_deep_finite_json(native):
    """Scope policy follows the real WS serializer, not an invented 256KiB/64-depth cap."""
    import json

    from tui_gateway.ws import WSTransport

    class Socket:
        def __init__(self):
            self.frames = []

        async def send_text(self, line):
            self.frames.append(json.loads(line))

    socket = Socket()
    viewer = connect(native.authority, transport=WSTransport(socket, asyncio.get_running_loop()))
    leases = []
    install(native, lambda request, params: leases.append(request.capture_scope()) or {"ok": True})
    try:
        await resume(viewer)
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})
        nested = {"leaf": True}
        for _ in range(72):
            nested = {"child": nested}
        payload = {"body": "x" * (300 * 1024), "deep": nested}
        assert await asyncio.to_thread(leases[-1].publish, "hermes-tern.btw.complete", payload)
        assert len(socket.frames) == 1
        assert socket.frames[0]["params"]["payload"]["data"] == payload
    finally:
        await viewer.close()

@pytest.mark.asyncio
async def test_scope_real_ws_rewind_after_valid_worker_read_cannot_publish_stale_frame(native, monkeypatch):
    """Genuine rewind after worker validation must veto the final registered WS send.

    The same mapped LiveSession, actor and subscription survive the receipt.
    Without a generation-writer-gated second read the stale plugin.event escapes.
    """
    import json

    from hermes_cli.plugin_gateway_scopes import GatewayScopeDeliveryError
    from tui_gateway.ws import WSTransport

    class Socket:
        def __init__(self):
            self.frames = []

        async def send_text(self, line):
            self.frames.append(json.loads(line))

    socket = Socket()
    transport = WSTransport(socket, asyncio.get_running_loop())
    leases = []
    install(native, lambda ctx, params: leases.append(ctx.capture_scope()) or {"ok": True})
    viewer = connect(native.authority, transport=transport)
    old_read = threading.Event()
    allow_publication = threading.Event()
    reading_lock = threading.Lock()
    worker_reads = 0
    original_get_session = native.db.get_session
    owner_thread = threading.get_ident()
    native.runner._evict_cached_agent = lambda route: None

    try:
        await resume(viewer)
        target_id = await asyncio.to_thread(native.db.append_message, "owned", "user", "rewind target")
        snapshot = await asyncio.to_thread(original_get_session, "owned")
        old_generation = snapshot["runtime_generation"]
        live = native.authority.sessions["owned"]
        subscription = viewer.subscriptions["owned"]
        assert "result" in await request(viewer, NAME, {"session_id": "owned"})

        def observed_get_session(sid):
            nonlocal worker_reads
            row = original_get_session(sid)
            if sid == "owned" and threading.get_ident() != owner_thread:
                with reading_lock:
                    worker_reads += 1
                    count = worker_reads
                if count == 2:
                    # Read completed with the OLD valid generation, but no
                    # final scoped frame has been admitted to the output yet.
                    assert row is not None and row["runtime_generation"] == old_generation
                    old_read.set()
                    assert allow_publication.wait(10), "rewind must commit before publication resumes"
            return row

        monkeypatch.setattr(native.db, "get_session", observed_get_session)
        publishing = asyncio.create_task(asyncio.to_thread(
            leases[0].publish, "hermes-tern.btw.complete", {"done": True},
        ))
        try:
            await async_wait_until(old_read.is_set, timeout=5, what="old valid generation read")
            # This is the real authority's session.mutate receipt transaction,
            # not a test-only SQL increment or a substituted delivery callback.
            reply = await asyncio.wait_for(request(viewer, "session.mutate", {
                "session_id": "owned", "request_id": "rewind-during-scoped-send",
                "expected_revision": snapshot["runtime_revision"],
                "expected_generation": old_generation, "operation": "rewind",
                "payload": {"target_message_id": target_id},
            }), timeout=5)
            assert "result" in reply, reply
            assert reply["result"]["execution_generation"] == old_generation + 1
            assert native.authority.sessions["owned"] is live
            assert viewer.subscriptions["owned"] == subscription
        finally:
            allow_publication.set()

        with pytest.raises(GatewayScopeDeliveryError):
            await asyncio.wait_for(publishing, timeout=5)
        assert not any(frame.get("params", {}).get("type") == "plugin.event"
                       for frame in socket.frames)
        assert worker_reads >= 3  # guarded final read after the rewind committed
        assert leases[0].cancellation.is_set()
    finally:
        allow_publication.set()
        monkeypatch.setattr(native.db, "get_session", original_get_session)
        await viewer.close()
