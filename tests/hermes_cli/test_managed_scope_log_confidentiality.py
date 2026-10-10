"""Regression evidence for managed-file parse warnings (related to #49836).

The warning must identify a rejected administrator file without copying YAML values
into persistent logs. These cases exercise the real managed loader, not a parser mock.
"""

import logging

import pytest


@pytest.mark.parametrize(
    ("invalid_yaml", "sentinel"),
    [
        ('provider_token: "SYNTHETIC_QUOTED_SECRET\n', "SYNTHETIC_QUOTED_SECRET"),
        ("provider_token: *SYNTHETIC_ALIAS_SECRET\n", "SYNTHETIC_ALIAS_SECRET"),
        ("provider_token: !SYNTHETIC_TAG_SECRET value\n", "SYNTHETIC_TAG_SECRET"),
    ],
)
def test_invalid_managed_yaml_warning_omits_values(
    tmp_path, monkeypatch, caplog, invalid_yaml, sentinel
):
    from hermes_cli import managed_scope

    managed = tmp_path / "managed"
    managed.mkdir()
    config = managed / "config.yaml"
    config.write_text(invalid_yaml, encoding="utf-8")
    monkeypatch.setenv("HERMES_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()

    with caplog.at_level(logging.WARNING, logger=managed_scope.__name__):
        assert managed_scope.load_managed_config() == {}

    warnings = [record for record in caplog.records if record.name == managed_scope.__name__]
    assert len(warnings) == 1
    warning = warnings[0]
    assert str(config) in warning.getMessage()
    assert "Admin policy from this file is NOT being applied" in warning.getMessage()
    assert sentinel not in warning.getMessage()
    assert warning.exc_info is None


def test_invalid_managed_yaml_is_not_cached_and_valid_reads_are_copied(
    tmp_path, monkeypatch, caplog
):
    from hermes_cli import managed_scope

    managed = tmp_path / "managed"
    managed.mkdir()
    config = managed / "config.yaml"
    monkeypatch.setenv("HERMES_MANAGED_DIR", str(managed))
    managed_scope.invalidate_managed_cache()

    with caplog.at_level(logging.WARNING, logger=managed_scope.__name__):
        assert managed_scope.load_managed_config() == {}
    assert not caplog.records

    config.write_text('model: "SYNTHETIC_BROKEN_SECRET\n', encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger=managed_scope.__name__):
        assert managed_scope.load_managed_config() == {}
        assert managed_scope.load_managed_config() == {}
    assert len([r for r in caplog.records if r.name == managed_scope.__name__]) == 2

    config.write_text("model:\n  default: managed/model\n", encoding="utf-8")
    first = managed_scope.load_managed_config()
    first["model"]["default"] = "mutated"
    assert managed_scope.load_managed_config() == {"model": {"default": "managed/model"}}
