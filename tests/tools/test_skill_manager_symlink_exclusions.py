"""Regression for #155776: excluded aliases must not consume realpath deduplication."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.skill_manager_tool import _find_skill


@pytest.mark.require_symlinks
def test_excluded_alias_does_not_hide_symlinked_external_skill(tmp_path):
    real = tmp_path / "shared" / "demo"
    real.mkdir(parents=True)
    (real / "SKILL.md").write_text(
        "---\nname: demo\ndescription: A shared skill.\n---\n\nBody\n",
        encoding="utf-8",
    )
    view = tmp_path / "external-view"
    view.mkdir()
    (view / ".archive").symlink_to(real, target_is_directory=True)
    (view / "demo").symlink_to(real, target_is_directory=True)

    # os.walk does not promise directory order. Exercise the valid traversal
    # where the excluded alias precedes the discoverable skill.
    real_walk = os.walk

    def excluded_first(*args, **kwargs):
        for directory, subdirs, files in real_walk(*args, **kwargs):
            if Path(directory) == view:
                subdirs.sort(key=lambda name: (name != ".archive", name))
            yield directory, subdirs, files

    with (
        patch("agent.skill_utils.get_all_skills_dirs", return_value=[view]),
        patch("tools.skill_manager_tool.os.walk", new=excluded_first),
    ):
        found = _find_skill("demo")

    assert found == {"path": view / "demo"}
