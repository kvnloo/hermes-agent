"""A new catalog default must not install over an existing core opt-out."""

from types import SimpleNamespace

import pytest

from hermes_cli import default_plugins, left_core_migration


def test_default_weixin_keeps_the_bundled_plugin_opt_out(tmp_path, monkeypatch):
    config = tmp_path / "config.yaml"
    config.write_text("plugins:\n  disabled: [platforms/weixin]\n", encoding="utf-8")
    calls = []
    monkeypatch.delenv("HERMES_DISABLE_LAZY_INSTALLS", raising=False)

    def install(name, *, discard=None):
        calls.append(name)
        return {"ok": True}

    monkeypatch.setattr(left_core_migration, "_install_into", lambda *a, **kw: install)
    entries = [SimpleNamespace(name="weixin", subdir="weixin")]
    for _ in range(2):
        assert default_plugins.install_defaults(tmp_path, entries=entries)["owed"] == []
        assert calls == []


@pytest.mark.parametrize(
    ("disabled", "expected"),
    [
        ("[weixin-platform]", []),
        ("[weixin]", []),
        ("platforms/weixin", ["weixin"]),
        ("[Platforms/Weixin]", ["weixin"]),
    ],
)
def test_default_respects_loader_list_and_exact_name_rules(tmp_path, monkeypatch, disabled, expected):
    config = tmp_path / "config.yaml"
    config.write_text(f"plugins:\n  enabled: [weixin]\n  disabled: {disabled}\n", encoding="utf-8")
    entries, calls = _observe_installs(monkeypatch)
    assert default_plugins.install_defaults(tmp_path, entries=entries)["installed"] == expected
    assert calls == expected


def _observe_installs(monkeypatch):
    calls = []
    monkeypatch.delenv("HERMES_DISABLE_LAZY_INSTALLS", raising=False)

    def install(name, *, discard=None):
        calls.append(name)
        return {"ok": True}

    monkeypatch.setattr(left_core_migration, "_install_into", lambda *a, **kw: install)
    return [SimpleNamespace(name="weixin", subdir="weixin")], calls


def test_default_reads_the_target_profiles_config(tmp_path, monkeypatch):
    profile = tmp_path / "profiles" / "second"
    profile.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text("plugins:\n  enabled: [weixin]\n", encoding="utf-8")
    (profile / "config.yaml").write_text("plugins:\n  disabled: [platforms/weixin]\n", encoding="utf-8")
    entries, calls = _observe_installs(monkeypatch)

    assert default_plugins.install_defaults(profile, entries=entries) == {"installed": [], "owed": []}
    assert calls == []
    assert default_plugins.install_defaults(tmp_path, entries=entries)["installed"] == ["weixin"]
    assert calls == ["weixin"]


def test_preexisting_disabled_install_still_has_its_removal_remembered(tmp_path, monkeypatch):
    installed = tmp_path / "plugins" / "weixin"
    installed.mkdir(parents=True)
    config = tmp_path / "config.yaml"
    config.write_text("plugins:\n  disabled: [weixin]\n", encoding="utf-8")
    entries, calls = _observe_installs(monkeypatch)

    assert default_plugins.install_defaults(tmp_path, entries=entries) == {"installed": [], "owed": []}
    installed.rmdir()
    # Keep the installer marker, but drop the old selection, as after cleaning up an uninstall.
    from hermes_cli.config_backend import write_config_key
    write_config_key(config, "plugins", {"disabled": []})

    assert default_plugins.install_defaults(tmp_path, entries=entries) == {"installed": [], "owed": []}
    assert calls == []
