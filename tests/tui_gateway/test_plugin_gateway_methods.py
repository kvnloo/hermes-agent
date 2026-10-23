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
