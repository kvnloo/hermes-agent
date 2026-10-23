"""Gateway registration boundaries and real plugin-loader rollback for #636."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest


def _owner(home: Path, name: str = "hermes-tern"):
    manager = PluginManager(scope_key=str(home))
    return PluginContext(PluginManifest(name=name, key=name), manager), manager


def _handler(request, params):
    return {"session": request.session_id, "value": params["value"]}


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    value: int


class LooseRequest(BaseModel):
    value: int


@pytest.mark.parametrize("name", [
    "browser.blocks", "gateway.capabilities", "hermes-tern", "hermes-tern.browser",
    "other.browser.blocks", "hermes-tern..blocks", "hermes-tern.browser.blocks!",
    "hermes-tern/browser.blocks", "hermes-tern.Browser.blocks",
])
def test_namespace_and_core_shadowing_fail_closed(tmp_path, name):
    owner, manager = _owner(tmp_path)
    with pytest.raises(ValueError):
        owner.register_gateway_method(name, _handler)
    assert manager._gateway_methods == {}


def test_reject_bad_handler_and_schema(tmp_path):
    owner, manager = _owner(tmp_path)
    for handler in (None, 42, lambda one: one):
        with pytest.raises(TypeError):
            owner.register_gateway_method("hermes-tern.browser.blocks", handler)

    async def async_handler(request, params):
        return {}

    with pytest.raises(TypeError):
        owner.register_gateway_method("hermes-tern.browser.blocks", async_handler)
    for invalid in ({"type": "object"}, int, LooseRequest):
        with pytest.raises(TypeError):
            owner.register_gateway_method("hermes-tern.browser.blocks", _handler, schema=invalid)
    assert not manager._gateway_methods


def test_duplicate_cross_plugin_claim_and_disposal(tmp_path):
    owner, manager = _owner(tmp_path)
    entry = owner.register_gateway_method("hermes-tern.browser.blocks", _handler, schema=StrictRequest)
    assert entry.active
    assert manager._gateway_methods[entry.key].schema is StrictRequest
    with pytest.raises(ValueError, match="already registered"):
        owner.register_gateway_method(entry.key, _handler)
    other = PluginContext(PluginManifest(name="other"), manager)
    with pytest.raises(ValueError, match="owned namespace"):
        other.register_gateway_method(entry.key, _handler)
    entry.dispose()
    assert entry.key not in manager._gateway_methods
    assert owner.register_gateway_method(entry.key, _handler).active


def test_profile_managers_and_targeted_unload_are_independent(tmp_path):
    alpha, a = _owner(tmp_path / "a")
    beta, b = _owner(tmp_path / "b")
    name = "hermes-tern.browser.blocks"
    first = alpha.register_gateway_method(name, _handler)
    second = beta.register_gateway_method(name, _handler)
    assert a._gateway_methods[name] is not b._gateway_methods[name]
    assert a.unload("hermes-tern")
    assert name not in a._gateway_methods
    assert name in b._gateway_methods
    assert not first.active and second.active
    assert b.unload()
    assert b._gateway_methods == {}


def _write_probe(home: Path, *, fail: bool = False) -> None:
    import hermes_yaml as yaml

    plugin_dir = home / "plugins" / "hermes-tern"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        yaml.safe_dump({"name": "hermes-tern", "version": "0.1.0", "description": "RPC fixture"}),
        encoding="utf-8",
    )
    (plugin_dir / "__init__.py").write_text(
        "def handler(request, params):\\n"
        "    request.assert_attached()\\n"
        "    return {'from': 'fixture', 'profile': request.profile}\\n"
        "def register(ctx):\\n"
        "    ctx.register_gateway_method('hermes-tern.browser.blocks', handler)\\n"
        + ("    raise RuntimeError('fixture failed after registration')\\n" if fail else ""),
        encoding="utf-8",
    )
    (home / "config.yaml").write_text(
        yaml.safe_dump({"plugins": {"enabled": ["hermes-tern"]}}), encoding="utf-8",
    )


@pytest.mark.parametrize("fails", [False, True])
def test_real_plugin_load_reload_and_failed_load_rollback(tmp_path, monkeypatch, fails):
    import hermes_cli.plugins as plugins_mod

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(plugins_mod, "get_bundled_plugins_dir", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr(PluginManager, "_scan_entry_points", lambda self: [])
    _write_probe(home, fail=fails)
    manager = PluginManager(scope_key=str(home))
    manager.discover_and_load()
    name = "hermes-tern.browser.blocks"
    if fails:
        assert not manager._plugins["hermes-tern"].enabled
        assert manager._plugins["hermes-tern"].error
        assert name not in manager._gateway_methods
        assert all(r.kind != "gateway_method" for r in manager._registration_order)
        return
    assert manager._plugins["hermes-tern"].enabled
    before = manager._gateway_methods[name]
    assert before.plugin_id == "hermes-tern"
    manager.discover_and_load(force=True)
    assert manager._gateway_methods[name] is not before
    manager.unload("hermes-tern")
    assert name not in manager._gateway_methods
