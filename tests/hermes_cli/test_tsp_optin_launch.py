"""Launcher cases adapted from review/134833-tsp-optin-gates (573b88c575).

This seam deliberately requires --tui as well as consent: unlike downstream preview,
it does not change bare Hermes routing and uses the SDK's TERN_TSP override rather
than introducing another HERMES_* setting environment variable.
"""
from types import SimpleNamespace

import pytest

from hermes_cli import main as m
from hermes_cli import main_tsp_launch as launch


@pytest.fixture(autouse=True)
def isolated_terminal(monkeypatch):
    for key in ("TERM_PROGRAM", "TERN_TSP", "HERMES_TUI", "TMUX", "STY", "ZELLIJ"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(m, "_EARLY_INTERFACE_CACHE", None)


def config(monkeypatch, value):
    from hermes_cli import config as cfg
    monkeypatch.setattr(cfg, "load_config", lambda: {"display": {"interface": "cli", "tern": value}})


def test_detection_alone_is_not_optin(monkeypatch):
    config(monkeypatch, False)
    assert not launch.tern_frontend_wanted({"TERM_PROGRAM": "tern"})


def test_config_enables_probe_only_inside_tern(monkeypatch):
    config(monkeypatch, True)
    assert launch.tern_frontend_wanted({"TERM_PROGRAM": "tern"})
    assert not launch.tern_frontend_wanted({})
    assert not launch.tern_frontend_wanted({"TERM_PROGRAM": "tern", "TERN_TSP": "0"})


@pytest.mark.parametrize("multiplexer", ("TMUX", "STY", "ZELLIJ"))
def test_force_never_bypasses_multiplexer_guard(monkeypatch, multiplexer):
    config(monkeypatch, True)
    assert not launch.tern_frontend_wanted({"TERN_TSP": "1", multiplexer: "active"})


def test_unreadable_config_fails_closed_but_sdk_override_can_probe(monkeypatch):
    from hermes_cli import config as cfg
    def broken():
        raise OSError("unreadable")
    monkeypatch.setattr(cfg, "load_config", broken)
    assert not launch.tern_frontend_wanted({"TERM_PROGRAM": "tern"})
    assert launch.tern_frontend_wanted({"TERN_TSP": "1"})


@pytest.mark.parametrize("value", [None, "true", 1, [], {}])
def test_only_literal_boolean_config_opts_in(monkeypatch, value):
    config(monkeypatch, value)
    assert not launch.tern_frontend_wanted({"TERM_PROGRAM": "tern"})


def test_cli_and_noninteractive_guards_still_win(monkeypatch):
    import sys
    config(monkeypatch, True)
    monkeypatch.setenv("TERM_PROGRAM", "tern")
    monkeypatch.setenv("TERN_TSP", "1")
    args = SimpleNamespace(cli=True, tui=False, tui_native=False)
    assert not m._resolve_use_tui(args)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert not m._resolve_use_tui(SimpleNamespace(cli=False, tui=False, tui_native=False))
    assert not m._wants_tui_early([])


def test_config_alone_does_not_change_classic_default(monkeypatch):
    import sys
    config(monkeypatch, True)
    monkeypatch.setenv("TERM_PROGRAM", "tern")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert not m._resolve_use_tui(SimpleNamespace(cli=False, tui=False, tui_native=False))


@pytest.mark.parametrize("code", [0, 42, 130, 75])
def test_no_handshake_only_falls_back_to_ink(monkeypatch, tmp_path, code):
    calls = []
    def run(argv, *, cwd, env):
        calls.append((argv, cwd, env))
        return code if "--tern-composer" in argv else 0
    monkeypatch.setattr(launch.subprocess, "call", run)
    env = {"HERMES_HOME": str(tmp_path)}
    result = launch.run_tui_frontend(["node", "entry.js"], tmp_path, env, probe=True)
    assert result == (0 if code == 75 else code)
    assert [call[0] for call in calls] == ([["node", "entry.js", "--tern-composer"], ["node", "entry.js"]] if code == 75 else [["node", "entry.js", "--tern-composer"]])
    assert all(call[1] == str(tmp_path) and call[2] is env for call in calls)


def test_real_child_exit_75_retries_same_ink_argv(tmp_path):
    import sys
    child = tmp_path / "frontend.py"
    receipt = tmp_path / "calls.txt"
    child.write_text(
        "import pathlib, sys\n"
        "p = pathlib.Path(sys.argv[1])\n"
        "with p.open('a') as f: f.write(('probe' if '--tern-composer' in sys.argv else 'ink') + '\\n')\n"
        "sys.exit(75 if '--tern-composer' in sys.argv else 0)\n"
    )
    assert launch.run_tui_frontend([sys.executable, str(child), str(receipt)], tmp_path, {}, probe=True) == 0
    assert receipt.read_text().splitlines() == ["probe", "ink"]


def test_disabled_or_dev_launch_does_not_probe(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(launch.subprocess, "call", lambda argv, **kwargs: calls.append(argv) or 0)
    assert launch.run_tui_frontend(["node", "entry.js"], tmp_path, {}, probe=False) == 0
    assert calls == [["node", "entry.js"]]
