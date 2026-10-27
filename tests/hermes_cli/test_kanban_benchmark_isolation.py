"""Isolation contracts for standalone Kanban benchmarks."""

import importlib.util
import os
from pathlib import Path


def _load_benchmark_module():
    path = Path(__file__).parents[1] / "stress" / "test_benchmarks.py"
    spec = importlib.util.spec_from_file_location("kanban_scale_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_benchmark_home_replaces_inherited_kanban_routing(monkeypatch, tmp_path):
    """A dispatched worker's board pins must not escape the benchmark sandbox."""
    production_db = tmp_path / "production" / "kanban.db"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(production_db))
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "zer0-company")
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "production"))
    monkeypatch.setenv("HERMES_KANBAN_WORKSPACES_ROOT", str(tmp_path / "workspaces"))

    benchmark = _load_benchmark_module()
    sandbox = tmp_path / "benchmark"
    benchmark.configure_benchmark_home(sandbox)

    assert os.environ["HERMES_HOME"] == str(sandbox)
    assert os.environ["HOME"] == str(sandbox)
    assert os.environ["HERMES_KANBAN_DB"] == str(sandbox / "kanban.db")
    assert "HERMES_KANBAN_BOARD" not in os.environ
    assert "HERMES_KANBAN_HOME" not in os.environ
    assert "HERMES_KANBAN_WORKSPACES_ROOT" not in os.environ

    from hermes_cli import kanban_db

    kanban_db.init_db()
    assert kanban_db.kanban_db_path() == sandbox / "kanban.db"
    assert not production_db.exists()
