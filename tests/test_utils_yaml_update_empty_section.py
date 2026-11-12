"""Single-key config updates must not orphan empty section mappings (regression for #154436)."""

import hermes_yaml as yaml

from utils import atomic_roundtrip_yaml_update


def test_removing_last_key_of_commented_section_preserves_parseable_config(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "skills:\n"
        "  # Nudge the agent to create skills.\n"
        "  creation_nudge_interval: 10\n"
        "\n"
        "  # Set to 0 to disable.\n"
        "agent:\n"
        "  max_turns: 5\n",
        encoding="utf-8",
    )

    atomic_roundtrip_yaml_update(path, "skills.creation_nudge_interval", None)

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {
        "skills": {},
        "agent": {"max_turns": 5},
    }
