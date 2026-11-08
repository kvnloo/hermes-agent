"""Regression for #125375: a registered launchd job is not a running gateway."""

import pytest

from hermes_cli import gateway as gateway_cli
from hermes_cli import gateway_launchd


@pytest.mark.parametrize("installed", [False, True], ids=["missing-plist", "existing-plist"])
@pytest.mark.parametrize("supervised_pid", [None, 4512], ids=["crash-loop", "booted"])
def test_launchd_start_reports_supervised_process(
    monkeypatch, tmp_path, capsys, installed, supervised_pid
):
    """An accepted kickstart must not report success for a PM workspace that exits."""
    plist = tmp_path / "ai.hermes.gateway.plist"
    if installed:
        plist.write_text("<plist/>", encoding="utf-8")

    marker = {"unsupported": True}
    monkeypatch.setattr(gateway_cli, "get_launchd_plist_path", lambda: plist)
    monkeypatch.setattr(gateway_cli, "get_launchd_label", lambda: "ai.hermes.gateway")
    monkeypatch.setattr(gateway_cli, "generate_launchd_plist", lambda: "<plist/>")
    monkeypatch.setattr(gateway_cli, "_refuse_temp_home_service_write", lambda *_: False)
    monkeypatch.setattr(gateway_cli, "_prepare_service_launcher", lambda: None)
    monkeypatch.setattr(gateway_cli, "refresh_launchd_plist_if_needed", lambda: True)
    monkeypatch.setattr(gateway_launchd, "_launchd_bootstrap_and_kickstart", lambda *_: True)
    monkeypatch.setattr(gateway_launchd, "_launchctl_kickstart_current", lambda *_: None)
    monkeypatch.setattr(gateway_cli, "_launchd_unsupported_marker_exists",
                        lambda: marker["unsupported"])
    monkeypatch.setattr(gateway_cli, "_clear_launchd_unsupported_marker",
                        lambda: marker.__setitem__("unsupported", False))
    monkeypatch.setattr(gateway_cli, "_launchctl_supervised_pid", lambda _: supervised_pid)
    # Use the real verifier without waiting for a wall-clock timeout.
    monkeypatch.setattr(
        gateway_cli, "wait_for_launchd_gateway_supervision",
        lambda **kw: gateway_launchd.wait_for_launchd_gateway_supervision(timeout=0, **kw),
    )

    if supervised_pid is None:
        with pytest.raises(SystemExit) as exc:
            gateway_launchd.launchd_start()
        assert exc.value.code == 1
        assert "✓ Service started" not in capsys.readouterr().out
    else:
        gateway_launchd.launchd_start()
        assert "✓ Service started" in capsys.readouterr().out
    assert marker["unsupported"] is False
