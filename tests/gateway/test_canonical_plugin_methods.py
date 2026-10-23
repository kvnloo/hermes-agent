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

from gateway.session_authority import LiveSession, SessionAuthority
from hermes_state import SessionDB
from hermes_state_runtime import begin_runtime_epoch
from tests.waiting import async_wait_until
from tui_gateway.ws import _authority_connection, _dispatch_request


NAME = "hermes-tern.surface.echo"
BETA_NAME = "beta-plugin.surface.echo"


class Transport:
    closed = False

    def write(self, _frame):
        return not self.closed


@pytest.fixture
def native(tmp_path, monkeypatch):
    import hermes_cli.plugins as plugins

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
        "            'value': params['value'], 'worker': threading.current_thread().name}\n"
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
        assert result["result"]["worker"].startswith("asyncio_")
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
