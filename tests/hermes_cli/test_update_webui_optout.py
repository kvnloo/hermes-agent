"""Regression for the persistent Web UI build opt-out in PR #83576."""

from unittest.mock import patch

from hermes_cli.main import _build_web_ui


def test_install_opt_out_skips_launch_build_until_marker_removed(tmp_path, monkeypatch):
    """An opted-out dashboard launch must not start Vite; opting back in must."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    web_dir = tmp_path / "web"
    web_dir.mkdir()
    (web_dir / "package.json").write_text("{}\n", encoding="utf-8")

    # The opt-out belongs to the install home, not to the dashboard source tree.
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)
    marker = home / ".skip-webui-build"
    marker.touch()

    with patch("hermes_cli.main._do_build_web_ui", return_value=True) as build:
        _build_web_ui(web_dir, fatal=True)
        build.assert_not_called()

        marker.unlink()
        _build_web_ui(web_dir, fatal=True)
        build.assert_called_once_with(web_dir, fatal=True)
