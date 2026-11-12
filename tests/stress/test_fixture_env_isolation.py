"""Regression coverage for directly executable stress harness environments."""

import os
from pathlib import Path
import subprocess
import sys

from tests.stress import test_atypical_scenarios as atypical
from tests.stress import test_subprocess_e2e as subprocess_e2e


def _hostile_env(tmp_path):
    return {
        "HERMES_KANBAN_DB": str(tmp_path / "production" / "kanban.db"),
        "Hermes_Kanban_Home": str(tmp_path / "production-home"),
        "HERMES_KANBAN_BOARD": "production",
        "PATH": "/bin",
    }


def test_subprocess_worker_env_removes_hostile_selectors_and_pins_db(tmp_path):
    hostile = _hostile_env(tmp_path)
    home = tmp_path / "disposable"
    env = subprocess_e2e.isolated_worker_env(str(home), hostile)

    selectors = {key: value for key, value in env.items() if key.upper().startswith("HERMES_KANBAN_")}
    assert selectors == {"HERMES_KANBAN_DB": str(home / "kanban.db")}
    env.update({"HERMES_HOME": str(home), "HOME": str(home)})
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from hermes_cli import kanban_db as kb; "
            "kb.init_db(); c=kb.connect(); "
            "kb.create_task(c, title='isolated subprocess', assignee='test'); c.close()",
        ],
        cwd=subprocess_e2e.WT,
        env=env,
        check=True,
    )
    assert (home / "kanban.db").exists()
    assert not Path(hostile["HERMES_KANBAN_DB"]).exists()


def test_atypical_scenario_env_removes_hostile_selectors_before_import(tmp_path, monkeypatch):
    hostile = _hostile_env(tmp_path)
    home = tmp_path / "disposable"
    for key, value in hostile.items():
        monkeypatch.setenv(key, value)

    atypical._pin_disposable_kanban_env(str(home))

    selectors = {
        key: value for key, value in os.environ.items() if key.upper().startswith("HERMES_KANBAN_")
    }
    assert selectors == {"HERMES_KANBAN_DB": str(home / "kanban.db")}
    for name in list(sys.modules):
        if name.startswith("hermes_cli"):
            del sys.modules[name]
    from hermes_cli import kanban_db as kb

    kb.init_db()
    conn = kb.connect()
    kb.create_task(conn, title="isolated direct import", assignee="test")
    conn.close()
    assert (home / "kanban.db").exists()
    assert not Path(hostile["HERMES_KANBAN_DB"]).exists()