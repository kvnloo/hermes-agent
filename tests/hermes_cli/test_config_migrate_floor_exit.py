"""CLI migration exit contract for NousResearch/hermes-agent#152717."""

from argparse import Namespace

import pytest

import hermes_cli.config as config


def test_config_migrate_below_floor_exits_nonzero_without_rewriting(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    # Avoid interactive optional-key prompts; keep the real migration and CLI handler.
    monkeypatch.setattr(config, "get_missing_env_vars", lambda **_kwargs: [])
    monkeypatch.setattr(config, "get_missing_skill_config_vars", lambda: [])
    monkeypatch.setattr(config, "_offer_new_optional_env_vars", lambda *_args: None)

    config_path = tmp_path / "config.yaml"
    original = "_config_version: 1\n"
    config_path.write_text(original, encoding="utf-8")
    args = Namespace(config_command="migrate")

    with pytest.raises(SystemExit) as exc:
        config.config_command(args)

    assert exc.value.code == 1
    assert config_path.read_text(encoding="utf-8") == original
    captured = capsys.readouterr()
    assert "can no longer be auto-migrated" in captured.err
    assert "Configuration updated!" not in captured.out

    # A current config is not a refusal: the same CLI command exits normally.
    _, latest = config.check_config_version()
    current = f"_config_version: {latest}\n"
    config_path.write_text(current, encoding="utf-8")
    config.config_command(args)
    assert config_path.read_text(encoding="utf-8") == current
