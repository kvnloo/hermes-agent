"""Dashboard Chat startup must distinguish a missing bundle from missing Node."""

from types import SimpleNamespace

import pytest

from hermes_cli import main_tui_launch
from hermes_cli.web_routers.chat_ws_errors import chat_start_failure_message


def test_missing_tui_workspace_reports_bundle_not_node(tmp_path, monkeypatch):
    monkeypatch.setattr(main_tui_launch, "_restore_tui_workspace", lambda _path: False)

    with pytest.raises(main_tui_launch.TuiLaunchError) as failure:
        main_tui_launch._ensure_tui_workspace(tmp_path / "ui-tui")

    assert failure.value.code == 1  # CLI still exits with its original status.
    assert failure.value.kind == "workspace_missing"
    message = chat_start_failure_message(failure.value)
    assert "TUI bundle is missing" in message
    assert "HERMES_TUI_DIR" in message
    assert "Node.js" not in message


def test_missing_node_keeps_actionable_node_guidance(monkeypatch):
    import pm

    monkeypatch.delenv("HERMES_NODE", raising=False)
    monkeypatch.setattr(pm, "ensure", lambda _bin: SimpleNamespace(env={"PATH": ""}))
    monkeypatch.setattr(main_tui_launch.shutil, "which", lambda *_args, **_kwargs: None)

    with pytest.raises(main_tui_launch.TuiLaunchError) as failure:
        main_tui_launch._tui_node_bin("node")

    assert failure.value.code == 1
    assert failure.value.kind == "node_missing"
    message = chat_start_failure_message(failure.value)
    assert "needs Node.js" in message
    assert "TUI bundle is missing" not in message


def test_other_system_exit_uses_generic_recovery():
    message = chat_start_failure_message(SystemExit(1))

    assert "Node.js" not in message
    assert "Check the server log" in message
