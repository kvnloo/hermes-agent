"""A superpowers 7.x Antigravity companion manifest is not a Hermes plugin (#125702)."""

import json

import hermes_yaml as yaml

from hermes_cli.plugins_discovery import scan_directory


def test_antigravity_manifest_is_skipped_without_warning(tmp_path, caplog):
    root = tmp_path / "plugins"
    superpowers = root / "superpowers"

    native = superpowers / ".hermes-plugin"
    native.mkdir(parents=True)
    (native / "plugin.yaml").write_text(
        yaml.safe_dump({
            "name": "superpowers",
            "version": "7.0.2",
            "description": "multi-harness plugin",
        })
    )

    foreign = superpowers / ".antigravity-plugin"
    foreign.mkdir()
    (foreign / "plugin.json").write_text(
        json.dumps({
            "name": "superpowers",
            "logo": "assets/logo.png",
            "suggestedPrompts": [],
            "category": "skills",
        })
    )

    with caplog.at_level("WARNING", logger="hermes_cli.plugins"):
        manifests = scan_directory(root, "user")

    assert [manifest.key for manifest in manifests] == ["superpowers/.hermes-plugin"]
    assert not [
        record for record in caplog.records
        if "Failed to parse" in record.getMessage()
    ]
