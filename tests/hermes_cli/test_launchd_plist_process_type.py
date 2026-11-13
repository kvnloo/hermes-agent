from hermes_cli import gateway as gateway_cli


def test_launchd_plist_marks_gateway_interactive(tmp_path, monkeypatch):
    """The long-lived gateway must not be throttled by macOS App Nap."""
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(gateway_cli, "get_hermes_home", lambda: home)
    monkeypatch.setattr(gateway_cli, "_stable_service_working_dir", lambda: str(home))
    monkeypatch.setattr(gateway_cli, "get_python_path", lambda: "/usr/bin/python3")
    monkeypatch.setattr(gateway_cli, "_detect_venv_dir", lambda: None)
    monkeypatch.setattr(gateway_cli, "_build_service_path_dirs", lambda: ["/usr/bin"])
    monkeypatch.setattr(gateway_cli.shutil, "which", lambda _name: None)

    plist = gateway_cli.generate_launchd_plist()

    assert "<key>ProcessType</key>\n    <string>Interactive</string>" in plist


def test_installed_legacy_plist_is_stale_after_interactive_upgrade(tmp_path, monkeypatch):
    """A pre-upgrade launchd daemon plist must be refreshed on next start."""
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(gateway_cli, "get_hermes_home", lambda: home)
    monkeypatch.setattr(gateway_cli, "_stable_service_working_dir", lambda: str(home))
    monkeypatch.setattr(gateway_cli, "get_python_path", lambda: "/usr/bin/python3")
    monkeypatch.setattr(gateway_cli, "_detect_venv_dir", lambda: None)
    monkeypatch.setattr(gateway_cli, "_build_service_path_dirs", lambda: ["/usr/bin"])
    monkeypatch.setattr(gateway_cli.shutil, "which", lambda _name: None)

    generated = gateway_cli.generate_launchd_plist()
    legacy = generated.replace(
        "    <key>ProcessType</key>\n    <string>Interactive</string>\n", ""
    )
    plist_path = tmp_path / "ai.hermes.gateway.plist"
    monkeypatch.setattr(gateway_cli, "get_launchd_plist_path", lambda: plist_path)

    plist_path.write_text(legacy, encoding="utf-8")
    assert gateway_cli.launchd_plist_is_current() is False

    plist_path.write_text(generated, encoding="utf-8")
    assert gateway_cli.launchd_plist_is_current() is True
