"""Consumer qualification of the author correction in upstream PR #125423."""

import json
import pytest

from hermes_constants import set_hermes_home_override, reset_hermes_home_override
from tools.skill_manager_tool import skill_manage
from tools.skills_tool import skill_view


def content(name, marker):
    return f"---\nname: {name}\ndescription: Use when testing local skill discovery.\n---\n\n{marker}\n"


def seed(path, name, marker):
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(content(name, marker), encoding="utf-8")


@pytest.mark.parametrize("support", ["references", "scripts", "templates", "assets"])
def test_support_document_does_not_block_create_across_profile_return(tmp_path, support):
    homes = [tmp_path / "profile-a", tmp_path / "profile-b"]
    for home in homes:
        seed(home / "skills" / "category" / "guide", "guide", "GUIDE")
        seed(home / "skills" / "category" / "guide" / support, support, "SUPPORT_ONLY")
    # Exercise public consumers with real home/config/discovery resolution, A→B→A.
    for index in [0, 1, 0]:
        token = set_hermes_home_override(homes[index])
        try:
            result = json.loads(skill_manage("create", support, content(support, f"PROFILE_{index}")))
            if index == 0 and (homes[0] / "visited").exists():
                assert result["success"] is False and "already exists" in result["error"], result
            else:
                assert result["success"] is True and not result.get("staged"), result
            viewed = json.loads(skill_view(support, preprocess=False))
            assert f"PROFILE_{index}" in viewed["content"], viewed
            assert "SUPPORT_ONLY" not in viewed["content"]
            assert (homes[index] / "skills" / "category" / "guide" / support / "SKILL.md").read_text(encoding="utf-8") == content(support, "SUPPORT_ONLY")
            (homes[index] / "visited").touch()
        finally:
            reset_hermes_home_override(token)


def test_support_named_category_remains_discoverable_and_blocks_duplicate(tmp_path):
    home = tmp_path / "profile"
    seed(home / "skills" / "scripts" / "guide", "guide", "CATEGORY_SKILL")
    token = set_hermes_home_override(home)
    try:
        result = json.loads(skill_manage("create", "guide", content("guide", "DUPLICATE")))
        assert result["success"] is False and "already exists" in result["error"], result
        viewed = json.loads(skill_view("guide", preprocess=False))
        assert "CATEGORY_SKILL" in viewed["content"], viewed
        assert not (home / "skills" / "guide").exists()
    finally:
        reset_hermes_home_override(token)
