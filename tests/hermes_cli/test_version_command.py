"""Tests for the /version slash command."""

from unittest.mock import patch

from cli import HermesCLI






def test_process_command_version_prints_version_info():
    cli_obj = HermesCLI.__new__(HermesCLI)

    with patch("hermes_cli.main._print_version_info") as mock_print:
        assert cli_obj.process_command("/version") is True

    mock_print.assert_called_once_with(check_updates=True)


def test_global_fast_version_skips_update_check(monkeypatch):
    from hermes_cli import _startup_fast

    calls = []
    monkeypatch.setattr(_startup_fast, "container_mode_may_be_active", lambda: False)
    monkeypatch.setattr(
        _startup_fast,
        "print_fast_version_info",
        lambda **kwargs: calls.append(kwargs),
    )

    assert _startup_fast.try_fast_version(["--version"]) is True
    assert calls == [{"check_updates": False}]


def test_global_version_never_enters_passive_source_check(monkeypatch, capsys, tmp_path):
    """Regression for #155862: liveness cannot wait for a missing release commit."""
    from hermes_cli import _startup_fast, banner, config, source_check

    checks = []
    monkeypatch.setattr(_startup_fast, "container_mode_may_be_active", lambda: False)
    monkeypatch.setattr(_startup_fast, "project_root_str", lambda: str(tmp_path))
    monkeypatch.setattr(_startup_fast, "read_openai_version", lambda: None)
    monkeypatch.setattr(banner, "format_banner_version_label", lambda: "Hermes Agent vtest")
    monkeypatch.setattr(config, "detect_install_method", lambda _root: "git")
    monkeypatch.setattr(
        source_check,
        "check_for_updates",
        lambda **kwargs: checks.append(kwargs) or {"behind": 0},
    )

    assert _startup_fast.try_fast_version(["--version"]) is True
    output = capsys.readouterr().out
    assert "Hermes Agent vtest" in output
    assert "Install method: git" in output
    assert checks == [], "a --version liveness probe must never attempt a passive release check"
