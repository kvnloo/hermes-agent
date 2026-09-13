from __future__ import annotations

import argparse

import pytest
from pathlib import Path

from hermes_cli.subcommands.plugins import build_plugins_parser


def _parse_plugins_args(*argv: str):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    build_plugins_parser(subparsers, cmd_plugins=lambda args: None)
    return parser.parse_args(["plugins", *argv])


def test_plugins_parser_exposes_doctor() -> None:
    doctor = _parse_plugins_args("doctor", "sample", "--ci")

    assert (doctor.plugins_action, doctor.target, doctor.ci) == (
        "doctor",
        "sample",
        True,
    )


def test_doctor_uses_registration_to_reject_bad_hook_and_callback_signature(
    tmp_path: Path,
) -> None:
    from hermes_cli.plugin_dev import doctor_plugin

    plugin = tmp_path / "bad-plugin"
    plugin.mkdir()
    (plugin / "plugin.yaml").write_text(
        "\n".join(
            [
                "name: bad-plugin",
                "version: 0.1.0",
                "description: broken contract",
                "provides_hooks:",
                "  - typo_hook",
                "  - pre_tool_call",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (plugin / "__init__.py").write_text(
        "def callback(tool_name):\n"
        "    return None\n\n"
        "def register(ctx):\n"
        "    ctx.register_hook('typo_hook', callback)\n"
        "    ctx.register_hook('pre_tool_call', callback)\n",
        encoding="utf-8",
    )

    report = doctor_plugin(plugin)
    messages = "\n".join(f.message for f in report.findings)
    assert report.ok is False
    assert "unknown hook 'typo_hook'" in messages
    assert "must accept **kwargs" in messages


def test_doctor_accepts_manifest_defaults_from_runtime_parser(tmp_path: Path) -> None:
    from hermes_cli.plugin_dev import doctor_plugin

    plugin = tmp_path / "minimal"
    plugin.mkdir()
    (plugin / "plugin.yaml").write_text("name: minimal\n", encoding="utf-8")
    (plugin / "__init__.py").write_text(
        "def register(ctx):\n    pass\n", encoding="utf-8"
    )

    report = doctor_plugin(plugin)
    assert report.ok, report.format_text()
    assert report.manifest is not None
    assert report.manifest.kind == "standalone"


def test_doctor_restores_global_tool_policy_and_module_state(tmp_path: Path) -> None:
    import sys

    from hermes_cli import plugins as plugins_mod
    from hermes_cli.plugin_dev import doctor_plugin
    from tools.registry import registry

    target = tmp_path / "cleanup-plugin"
    target.mkdir()
    (target / "plugin.yaml").write_text(
        "name: cleanup-plugin\nprovides_tools: [cleanup_plugin_ping]\n",
        encoding="utf-8",
    )
    (target / "__init__.py").write_text(
        "import json\n\n"
        "def ping(args, **kwargs):\n    return json.dumps({'ok': True})\n\n"
        "def register(ctx):\n"
        "    ctx.register_tool(name='cleanup_plugin_ping', toolset='cleanup', "
        "schema={'name': 'cleanup_plugin_ping', 'description': 'test', "
        "'parameters': {'type': 'object'}}, handler=ping)\n",
        encoding="utf-8",
    )

    before_policy = dict(registry._plugin_override_policy)
    before_scoped = set(registry._scoped_tools)
    before_module_scopes = {
        ns: set(scopes) for ns, scopes in registry._plugin_module_scopes.items()
    }
    before_bare = dict(plugins_mod._BARE_MODULE_SCOPE)
    before_modules = {
        name
        for name in sys.modules
        if name == "hermes_plugins" or name.startswith("hermes_plugins.")
    }

    report = doctor_plugin(target)

    assert report.ok, report.format_text()
    assert report.registered_tools == ("cleanup_plugin_ping",)
    assert registry.get_entry("cleanup_plugin_ping") is None
    assert registry._plugin_override_policy == before_policy
    assert set(registry._scoped_tools) == before_scoped
    assert {
        ns: set(scopes) for ns, scopes in registry._plugin_module_scopes.items()
    } == before_module_scopes
    assert plugins_mod._BARE_MODULE_SCOPE == before_bare
    assert registry.plugin_scope_for_module("hermes_plugins.cleanup_plugin") is None
    after_modules = {
        name
        for name in sys.modules
        if name == "hermes_plugins" or name.startswith("hermes_plugins.")
    }
    assert after_modules == before_modules


def test_doctor_blocks_live_network(tmp_path: Path) -> None:
    from hermes_cli.plugin_dev import doctor_plugin

    plugin = tmp_path / "network-plugin"
    plugin.mkdir()
    (plugin / "plugin.yaml").write_text("name: network-plugin\n", encoding="utf-8")
    (plugin / "__init__.py").write_text(
        "import socket\n\n"
        "def register(ctx):\n"
        "    socket.create_connection(('example.com', 443))\n",
        encoding="utf-8",
    )

    report = doctor_plugin(plugin)
    assert report.ok is False
    assert "network access is disabled while Plugin Doctor runs" in report.format_text()


def test_resolve_rejects_directory_without_manifest(tmp_path: Path) -> None:
    """A non-plugin directory must not resolve — Doctor copies what it resolves."""
    from hermes_cli.plugin_dev import resolve_plugin_path

    not_a_plugin = tmp_path / "home"
    (not_a_plugin / "Documents").mkdir(parents=True)
    (not_a_plugin / "Documents" / "notes.txt").write_text("x", encoding="utf-8")

    with pytest.raises(FileNotFoundError) as excinfo:
        resolve_plugin_path(not_a_plugin)

    assert "holds no plugin manifest" in str(excinfo.value)


def test_doctor_default_target_does_not_copy_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    """``hermes plugins doctor`` with no argument defaults to ``.``.

    Before the manifest guard, that copied the whole working directory into
    a temporary HERMES_HOME — running it from ``$HOME`` copied the home
    directory, cloud-storage placeholders included.
    """
    import os
    import shutil

    from hermes_cli import plugin_dev

    workdir = tmp_path / "workdir"
    (workdir / "big").mkdir(parents=True)
    (workdir / "big" / "payload.bin").write_text("x" * 1024, encoding="utf-8")
    monkeypatch.chdir(workdir)

    copied: list[tuple[str, str]] = []
    real_copytree = shutil.copytree

    def _tracking_copytree(src, dst, *args, **kwargs):
        copied.append((os.fspath(src), os.fspath(dst)))
        return real_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(plugin_dev.shutil, "copytree", _tracking_copytree)

    report = plugin_dev.doctor_plugin()

    assert report.ok is False
    assert copied == []


def test_resolve_accepts_category_layout(tmp_path: Path) -> None:
    """A category directory holds no manifest itself but discovery finds one."""
    from hermes_cli.plugin_dev import resolve_plugin_path

    category = tmp_path / "image_gen"
    plugin = category / "openai"
    plugin.mkdir(parents=True)
    (plugin / "plugin.yaml").write_text("name: openai\n", encoding="utf-8")

    assert resolve_plugin_path(category) == category.resolve()


def test_resolve_prefers_installed_id_over_unrelated_local_dir(
    tmp_path: Path, monkeypatch
) -> None:
    """A same-named local directory must not shadow the installed plugin."""
    from hermes_cli import plugin_dev

    hermes_home = tmp_path / "hermes-home"
    installed = hermes_home / "plugins" / "sample"
    installed.mkdir(parents=True)
    (installed / "plugin.yaml").write_text("name: sample\n", encoding="utf-8")

    workdir = tmp_path / "workdir"
    (workdir / "sample").mkdir(parents=True)
    monkeypatch.chdir(workdir)
    monkeypatch.setattr(plugin_dev, "get_hermes_home", lambda: hermes_home)

    assert plugin_dev.resolve_plugin_path("sample") == installed.resolve()


def test_doctor_removes_temp_home_when_staging_copy_fails(
    tmp_path: Path, monkeypatch
) -> None:
    """A copy failure (e.g. ENOSPC) must not strand a hermes-plugin-doctor-* dir."""
    import errno
    import shutil
    import tempfile



    from hermes_cli import plugin_dev

    plugin = tmp_path / "sample"
    plugin.mkdir()
    (plugin / "plugin.yaml").write_text("name: sample\n", encoding="utf-8")
    (plugin / "__init__.py").write_text(
        "def register(ctx):\n    pass\n", encoding="utf-8"
    )

    scratch = tmp_path / "scratch-tmp"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))

    def _enospc(*_args, **_kwargs):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(shutil, "copytree", _enospc)

    caught: OSError | None = None
    try:
        with plugin_dev._doctor_runtime(plugin):
            pass  # pragma: no cover - staging fails before yield
    except OSError as exc:
        caught = exc

    assert caught is not None and caught.errno == errno.ENOSPC
    # Check for leftovers WHILE the exception (and its traceback frames) is
    # still referenced: the old code relied on TemporaryDirectory's GC
    # finalizer, which cannot run while the traceback pins the frame — the
    # exact window where a stranded hermes-plugin-doctor-* dir was observed.
    leftovers = list(scratch.glob("hermes-plugin-doctor-*"))
    assert leftovers == [], f"stranded doctor temp dirs: {leftovers}"


def _write_tool_plugin(plugin_dir: Path, name: str, tool: str) -> None:
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        f"name: {name}\nprovides_tools: [{tool}]\n", encoding="utf-8"
    )
    init = (
        "import json\n\n"
        "def handler(args, **kwargs):\n    return json.dumps({'ok': True})\n\n"
        "def register(ctx):\n"
        "    ctx.register_tool(name='__TOOL__', toolset='probe', "
        "schema={'name': '__TOOL__', 'description': 't', "
        "'parameters': {'type': 'object'}}, handler=handler)\n"
    ).replace("__TOOL__", tool)
    (plugin_dir / "__init__.py").write_text(init, encoding="utf-8")


def test_doctor_does_not_mangle_subsequent_real_load_of_same_named_plugin(
    tmp_path: Path, monkeypatch
) -> None:
    """A doctor run must not pin ``_BARE_MODULE_SCOPE`` for a later real load.

    Regression guard for the namespace-mangling observable: before the fix a
    doctor of ``leak`` left ``_BARE_MODULE_SCOPE['hermes_plugins.leak']``
    pointing at the (since-deleted) temp home, so a subsequent real load of a
    same-named plugin from a different ``HERMES_HOME`` was forced into the
    ``hermes_plugins.leak__home_<hash>`` namespace instead of the bare name.
    """
    import shutil

    from hermes_cli import plugins as plugins_mod
    from hermes_cli.plugin_dev import doctor_plugin
    from hermes_cli.plugins import PluginManager

    src = tmp_path / "plugin-leak"
    _write_tool_plugin(src, "leak", "leak_tool_a")

    report = doctor_plugin(src)
    assert report.ok, report.format_text()
    assert plugins_mod._BARE_MODULE_SCOPE.get("hermes_plugins.leak") is None

    real_home = tmp_path / "real-home"
    (real_home / "plugins").mkdir(parents=True)
    (real_home / "bundled-plugins").mkdir(parents=True)
    shutil.copytree(src, real_home / "plugins" / "plugin-leak")
    monkeypatch.setenv("HERMES_HOME", str(real_home))
    monkeypatch.setenv("HERMES_BUNDLED_PLUGINS", str(real_home / "bundled-plugins"))
    monkeypatch.setenv("HERMES_ENABLE_PROJECT_PLUGINS", "0")

    mgr = PluginManager()
    manifest = mgr._scan_directory(real_home / "plugins", source="user")[0]
    module_name = mgr._directory_module_name(manifest)
    assert module_name == "hermes_plugins.leak"
    assert "__home_" not in module_name

    with plugins_mod._MODULE_NAMESPACE_LOCK:
        plugins_mod._BARE_MODULE_SCOPE.pop("hermes_plugins.leak", None)


def test_doctor_repeated_runs_of_same_named_plugin_use_bare_namespace(
    tmp_path: Path,
) -> None:
    """Two consecutive doctor runs of a same-named plugin must both use the bare
    namespace. Without the cleanup, run 1's ``_BARE_MODULE_SCOPE`` entry survives
    and run 2 (in a different temp home) is mangled to ``__home_<hash>``.
    """
    from hermes_cli.plugin_dev import _doctor_runtime

    _write_tool_plugin(tmp_path / "leak-a", "leak", "leak_tool_a")
    _write_tool_plugin(tmp_path / "leak-b", "leak", "leak_tool_b")

    with _doctor_runtime(tmp_path / "leak-a") as host1:
        loaded1 = host1.manager._plugins.get(host1.manifest.key or host1.manifest.name)
        name1 = loaded1.module.__name__
    with _doctor_runtime(tmp_path / "leak-b") as host2:
        loaded2 = host2.manager._plugins.get(host2.manifest.key or host2.manifest.name)
        name2 = loaded2.module.__name__

    assert name1 == "hermes_plugins.leak"
    assert name2 == "hermes_plugins.leak"
    assert "__home_" not in name2


def test_doctor_restores_state_when_plugin_import_fails(tmp_path: Path) -> None:
    """A plugin whose ``__init__`` raises at import still mutates the
    process-global attribution maps (``_directory_module_name`` runs before the
    import; ``register_plugin_override_policy`` runs before the import). The
    doctor's restore contract must revert them even on this failure path, where
    ``_clear_plugin_submodules`` cannot see ``loaded.module`` (it is ``None``).
    """
    import sys

    from hermes_cli import plugins as plugins_mod
    from hermes_cli.plugin_dev import doctor_plugin
    from tools.registry import registry

    target = tmp_path / "boom-plugin"
    target.mkdir()
    (target / "plugin.yaml").write_text("name: boom-plugin\n", encoding="utf-8")
    (target / "__init__.py").write_text(
        "raise RuntimeError('boom at import')\n", encoding="utf-8"
    )

    before_policy = dict(registry._plugin_override_policy)
    before_scoped = set(registry._scoped_tools)
    before_module_scopes = {
        ns: set(scopes) for ns, scopes in registry._plugin_module_scopes.items()
    }
    before_bare = dict(plugins_mod._BARE_MODULE_SCOPE)
    before_modules = {
        name
        for name in sys.modules
        if name == "hermes_plugins" or name.startswith("hermes_plugins.")
    }

    report = doctor_plugin(target)

    assert report.ok is False
    assert registry._plugin_override_policy == before_policy
    assert set(registry._scoped_tools) == before_scoped
    assert {
        ns: set(scopes) for ns, scopes in registry._plugin_module_scopes.items()
    } == before_module_scopes
    assert plugins_mod._BARE_MODULE_SCOPE == before_bare
    assert "hermes_plugins.boom_plugin" not in plugins_mod._BARE_MODULE_SCOPE
    assert registry.plugin_scope_for_module("hermes_plugins.boom_plugin") is None
    after_modules = {
        name
        for name in sys.modules
        if name == "hermes_plugins" or name.startswith("hermes_plugins.")
    }
    assert after_modules == before_modules
