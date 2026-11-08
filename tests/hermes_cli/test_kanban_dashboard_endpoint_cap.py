"""Dashboard dispatch must pass the endpoint quota cap to the shared dispatcher.

The existing dashboard cap-bypass report is #127446 (liuhao1024); this
extends that invariant to rollinTaters' endpoint caps in PR #151219.
"""

from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path


def _dashboard_api():
    name = "kanban_dashboard_endpoint_cap_test_api"
    path = Path(__file__).resolve().parents[2] / "plugins" / "kanban" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def _fake_board_conn(board=None):
    yield board, object()


def test_dashboard_dispatch_passes_configured_endpoint_cap(monkeypatch):
    """A dashboard nudge must not bypass the provider endpoint's capacity."""
    from hermes_cli import config
    from hermes_cli import kanban_db_dispatch as kbd

    api = _dashboard_api()
    monkeypatch.setattr(api, "_board_conn", _fake_board_conn)
    monkeypatch.setattr(config, "load_config_readonly", lambda: {
        "kanban": {"max_in_progress_per_endpoint": {
            "localhost:11434": 1, "OPENROUTER": "2",
        }},
    })

    captured = {}

    def fake_dispatch_once(conn, **kwargs):
        captured.update(kwargs)
        return kbd.DispatchResult()

    monkeypatch.setattr(kbd, "dispatch_once", fake_dispatch_once)
    api.dispatch(dry_run=True, max_n=5, board=None)

    assert captured["max_in_progress_per_endpoint"] == {
        "localhost:11434": 1, "openrouter": 2,
    }
    assert captured["max_spawn"] == 5
    assert captured["dry_run"] is True
