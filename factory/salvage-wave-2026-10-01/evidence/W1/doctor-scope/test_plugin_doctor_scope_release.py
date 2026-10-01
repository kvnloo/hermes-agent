"""W1 salvage regression: Plugin Doctor must release process-global plugin
attribution for its temp HERMES_HOME (module scopes + bare-namespace claim)."""
from pathlib import Path


def _write_tool_plugin(plugin_dir: Path, name: str, tool: str) -> None:
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        f"name: {name}\nprovides_tools: [{tool}]\n", encoding="utf-8"
    )
    (plugin_dir / "__init__.py").write_text(
        "import json\n\n"
        "def handler(args, **kwargs):\n    return json.dumps({'ok': True})\n\n"
        "def register(ctx):\n"
        f"    ctx.register_tool(name='{tool}', toolset='probe', "
        f"schema={{'name': '{tool}', 'description': 't', "
        "'parameters': {'type': 'object'}}, handler=handler)\n",
        encoding="utf-8",
    )


def test_doctor_releases_module_scope_attribution(tmp_path: Path) -> None:
    """After doctor returns, no module namespace may still map to its (deleted)
    temp HERMES_HOME scope."""
    from hermes_cli.plugin_dev import doctor_plugin
    from tools.registry import registry

    _write_tool_plugin(tmp_path / "scopeprobe", "scopeprobe", "scopeprobe_ping")
    before = {ns: set(s) for ns, s in registry._plugin_module_scopes.items()}

    report = doctor_plugin(tmp_path / "scopeprobe")

    assert report.ok, report.format_text()
    assert registry.plugin_scope_for_module("hermes_plugins.scopeprobe") is None
    assert {ns: set(s) for ns, s in registry._plugin_module_scopes.items()} == before


def test_repeated_doctor_runs_keep_bare_namespace(tmp_path: Path) -> None:
    """Two doctor runs of a same-named plugin in one process must both import
    under the bare ``hermes_plugins.<slug>`` namespace (run 1 must not keep its
    _BARE_MODULE_SCOPE claim and force run 2 into ``__home_<digest>``)."""
    from hermes_cli.plugin_dev import _doctor_runtime

    _write_tool_plugin(tmp_path / "a" / "barepro", "barepro", "barepro_a")
    _write_tool_plugin(tmp_path / "b" / "barepro", "barepro", "barepro_b")

    names = []
    for root in ("a", "b"):
        with _doctor_runtime(tmp_path / root / "barepro") as host:
            loaded = host.manager._plugins.get(host.manifest.key or host.manifest.name)
            names.append(loaded.module.__name__)

    assert names == ["hermes_plugins.barepro", "hermes_plugins.barepro"]
