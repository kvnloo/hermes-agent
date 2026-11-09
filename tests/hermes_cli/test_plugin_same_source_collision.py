"""Regression for #121078: a same-source backup must not displace the live plugin.

Builds on kanederkson's discovery warning in #151614. The reporter was TARSDrakon.
"""

import logging
from pathlib import Path

import pytest

from hermes_cli.plugins_discovery import resolve_manifest_winners, scan_directory


@pytest.mark.parametrize("source", ["user", "project"])
def test_canonical_plugin_survives_later_same_source_backup(tmp_path, caplog, source):
    plugin_root = tmp_path / "plugins"
    for directory in ("foo", "foo.bak-20260924"):
        location = plugin_root / directory
        location.mkdir(parents=True)
        (location / "plugin.yaml").write_text(
            "name: foo\nversion: 0.1.0\ndescription: test plugin\n",
            encoding="utf-8",
        )

    manifests = scan_directory(plugin_root, source)
    assert len(manifests) == 2  # Both candidates are valid and discovered.

    with caplog.at_level(logging.WARNING, logger="hermes_cli.plugins"):
        winners = resolve_manifest_winners(manifests)

    assert set(winners) == {"foo"}
    assert Path(winners["foo"].path).name == "foo"
    assert str(plugin_root / "foo") in caplog.text
    assert str(plugin_root / "foo.bak-20260924") in caplog.text
