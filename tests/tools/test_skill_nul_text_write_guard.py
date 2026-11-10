"""Skill writes must not persist NUL text that read_file will classify as binary."""

from unittest.mock import patch

from tools.skill_manager_tool import _create_skill, _edit_skill, _patch_skill, _write_file


SKILL_TEXT = (
    "---\nname: nul-guard\ndescription: Check safe text writes.\n---\n"
    "\n# Skill\n\nbody\n"
)


def test_skill_manage_rejects_nul_before_any_text_write(tmp_path):
    with patch("tools.skill_manager_tool.SKILLS_DIR", tmp_path), patch(
        "agent.skill_utils.get_all_skills_dirs", return_value=[tmp_path]
    ):
        bad_create = _create_skill("bad-skill", SKILL_TEXT.replace("body", "b\x00ody"))
        assert bad_create["success"] is False
        assert "NUL" in bad_create["error"]
        assert not (tmp_path / "bad-skill" / "SKILL.md").exists()

        assert _create_skill("safe-skill", SKILL_TEXT)["success"] is True
        skill_path = tmp_path / "safe-skill" / "SKILL.md"
        bad_edit = _edit_skill("safe-skill", SKILL_TEXT.replace("body", "b\x00ody"))
        assert bad_edit["success"] is False
        assert "NUL" in bad_edit["error"]
        assert skill_path.read_text() == SKILL_TEXT

        assert _write_file("safe-skill", "references/notes.md", "initial\n")["success"] is True
        target = tmp_path / "safe-skill" / "references" / "notes.md"
        bad_patch = _patch_skill(
            "safe-skill", "initial", "in\x00itial", file_path="references/notes.md"
        )
        assert bad_patch["success"] is False
        assert "NUL" in bad_patch["error"]
        assert target.read_bytes() == b"initial\n"

        bad_write = _write_file("safe-skill", "references/notes.md", "in\x00itial\n")
        assert bad_write["success"] is False
        assert "NUL" in bad_write["error"]
        assert target.read_bytes() == b"initial\n"
