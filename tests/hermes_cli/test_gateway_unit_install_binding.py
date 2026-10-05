"""Persisted supervisor commands bind to the install root, never a dependency
generation workspace (#131164).

A generation's venv console script runs with PROJECT_ROOT inside
``installs/<key>/environments/<gen>/workspace``. A unit generated from there
crash-loops with "no dependency environment is committed" (that key has no
recorded environment, and the tree is GC-able), so generation must map back to
the owning checkout — and when they cannot, the write must be refused.
"""
import hermes_cli.gateway as gateway_cli
from pm.environments import install_state_dir


def _workspace_rooted_install(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    checkout = tmp_path / "checkout"
    (checkout / "pm").mkdir(parents=True)
    (checkout / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    state = install_state_dir(checkout)
    workspace = state / "environments" / ("g" * 32) / "workspace"
    (workspace / "pm").mkdir(parents=True)
    (workspace / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    (state / "inputs").mkdir(parents=True)
    (state / "inputs" / ".project-root").write_text(str(checkout), encoding="utf-8")
    return checkout, workspace


def test_generate_systemd_unit_launches_from_owning_checkout(tmp_path, monkeypatch):
    checkout, workspace = _workspace_rooted_install(tmp_path, monkeypatch)
    monkeypatch.setattr(gateway_cli, "PROJECT_ROOT", workspace)

    unit = gateway_cli.generate_systemd_unit(system=False)

    exec_lines = [line for line in unit.splitlines()
                  if line.strip().startswith(("ExecStart", "ExecStop"))]
    assert exec_lines, "unit must carry launch commands"
    assert all(str(checkout.resolve()) in line for line in exec_lines), (
        "Exec lines must reference the owning checkout, not the generation workspace")
    assert str(workspace) not in unit


def test_refresh_refuses_to_write_a_generation_launcher_unit(tmp_path, monkeypatch, capsys):
    checkout, workspace = _workspace_rooted_install(tmp_path, monkeypatch)
    monkeypatch.setattr(gateway_cli, "PROJECT_ROOT", workspace)
    unit_path = tmp_path / "hermes-gateway.service"
    unit_path.write_text("old unit\n", encoding="utf-8")
    # A synthetic path: the tmp_path fixture lives under /tmp/pytest-of-, which
    # the pre-existing pytest-marker safety belt refuses before this guard runs.
    poisoned_exec = "/srv/hermes-home/installs/aabbcc/environments/" + ("g" * 32) + "/workspace/.hermes/bin/hermes"
    poisoned = (
        "[Service]\n"
        f'ExecStart="{poisoned_exec}" "gateway" "run"\n'
    )
    monkeypatch.setattr(gateway_cli, "get_systemd_unit_path", lambda system=False: unit_path)
    monkeypatch.setattr(gateway_cli, "generate_systemd_unit",
                        lambda system=False, run_as_user=None: poisoned)
    monkeypatch.setattr(gateway_cli, "_sync_hermes_home_from_systemd_unit", lambda **_: None)
    ran = []
    monkeypatch.setattr(gateway_cli, "_run_systemctl", lambda args, **kwargs: ran.append(args))

    assert gateway_cli.refresh_systemd_unit_if_needed(system=False) is False
    assert unit_path.read_text(encoding="utf-8") == "old unit\n"
    assert not any("daemon-reload" in str(args) for args in ran)
    out = capsys.readouterr().out
    assert "dependency-generation tree" in out
    assert str(checkout / ".hermes" / "bin" / "hermes") in out


def test_generation_launcher_in_plist_scans_launch_entries_not_path_values():
    gen = "/srv/hermes-home/installs/aabbcc/environments/" + ("g" * 32)
    plist_launch = (
        "<key>ProgramArguments</key>\n<array>\n"
        f"<string>{gen}/workspace/.hermes/bin/hermes</string>\n"
        "<string>gateway</string>\n</array>\n"
    )
    plist_venv_script = f"<string>{gen}/venv/bin/hermes</string>\n"
    plist_path_value = f"<string>/usr/bin:{gen}/venv/bin</string>\n"

    assert gateway_cli._generation_launcher_in_plist(plist_launch) is not None
    assert gateway_cli._generation_launcher_in_plist(plist_venv_script) is not None
    assert gateway_cli._generation_launcher_in_plist(plist_path_value) is None, (
        "a PATH value carrying a generation bin dir must not trip the plist scan")


def test_systemd_install_refuses_a_generation_launcher_unit(tmp_path, monkeypatch, capsys):
    checkout, workspace = _workspace_rooted_install(tmp_path, monkeypatch)
    monkeypatch.setattr(gateway_cli, "PROJECT_ROOT", workspace)
    unit_path = tmp_path / "hermes-gateway.service"
    poisoned_exec = "/srv/hermes-home/installs/aabbcc/environments/" + ("g" * 32) + "/workspace/.hermes/bin/hermes"
    monkeypatch.setattr(gateway_cli, "get_systemd_unit_path", lambda system=False: unit_path)
    monkeypatch.setattr(gateway_cli, "has_legacy_hermes_units", lambda: False)
    monkeypatch.setattr(gateway_cli, "generate_systemd_unit",
                        lambda system=False, run_as_user=None: f'[Service]\nExecStart="{poisoned_exec}" "gateway" "run"\n')
    ran = []
    monkeypatch.setattr(gateway_cli, "_run_systemctl", lambda args, **kwargs: ran.append(args))

    gateway_cli.systemd_install()

    assert not unit_path.exists(), "a poisoned unit must not be installed"
    assert ran == []
    assert "dependency-generation tree" in capsys.readouterr().out


def test_pm_repair_rewrites_generation_launcher_units(tmp_path, monkeypatch, capsys):
    _checkout, workspace = _workspace_rooted_install(tmp_path, monkeypatch)
    monkeypatch.setattr(gateway_cli, "PROJECT_ROOT", workspace)
    monkeypatch.setattr(gateway_cli, "get_launchd_plist_path", lambda: tmp_path / "absent.plist")
    unit_path = tmp_path / "hermes-gateway.service"
    unit_path.write_text(
        f'[Service]\nExecStart="{workspace}/.hermes/bin/hermes" "gateway" "run"\n',
        encoding="utf-8")
    refreshed = []

    def fake_refresh(system=False):
        refreshed.append(system)
        unit_path.write_text(
            '[Service]\nExecStart="/opt/hermes/.hermes/bin/hermes" "gateway" "run"\n',
            encoding="utf-8")
        return True

    monkeypatch.setattr(gateway_cli, "get_systemd_unit_path", lambda system=False: unit_path)
    monkeypatch.setattr(gateway_cli, "refresh_systemd_unit_if_needed", fake_refresh)

    from pm import cli as pm_cli

    pm_cli._heal_generation_launcher_service_units()

    assert refreshed == [False], "user scope healed; the now-clean file skips the system scope"
    assert "✓ Rewrote the gateway user service" in capsys.readouterr().out

    # A clean definition is left alone.
    pm_cli._heal_generation_launcher_service_units()
    assert refreshed == [False]


def test_pm_repair_warns_when_the_unit_still_cannot_be_healed(tmp_path, monkeypatch, capsys):
    _checkout, workspace = _workspace_rooted_install(tmp_path, monkeypatch)
    monkeypatch.setattr(gateway_cli, "PROJECT_ROOT", workspace)
    monkeypatch.setattr(gateway_cli, "get_launchd_plist_path", lambda: tmp_path / "absent.plist")
    unit_path = tmp_path / "hermes-gateway.service"
    poisoned = f'[Service]\nExecStart="{workspace}/.hermes/bin/hermes" "gateway" "run"\n'
    unit_path.write_text(poisoned, encoding="utf-8")
    refreshed = []
    monkeypatch.setattr(gateway_cli, "get_systemd_unit_path", lambda system=False: unit_path)
    monkeypatch.setattr(gateway_cli, "refresh_systemd_unit_if_needed",
                        lambda system=False: refreshed.append(system) or False)

    from pm import cli as pm_cli

    pm_cli._heal_generation_launcher_service_units()

    assert refreshed == [False, True], "both scopes were examined and stayed poisoned"
    captured = capsys.readouterr()
    assert "✓ Rewrote" not in captured.out
    assert "still launches from a dependency-generation tree" in captured.err
