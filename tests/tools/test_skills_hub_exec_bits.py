"""A skill script committed executable stays executable after a hub install."""

import os
import stat
from unittest.mock import MagicMock, patch

import pytest

from tools.skills_hub_github import GitHubAuth, GitHubSource
from tools.skills_hub_install import quarantine_bundle

pytestmark = pytest.mark.platforms("posix")


def _quarantine(tmp_path, bundle):
    import tools.skills_hub as hub
    hub_dir = tmp_path / "skills" / ".hub"
    with patch.object(hub, "SKILLS_DIR", tmp_path / "skills"), \
         patch.object(hub, "HUB_DIR", hub_dir), \
         patch.object(hub, "QUARANTINE_DIR", hub_dir / "quarantine"):
        return quarantine_bundle(bundle)


def _is_exec(path):
    return bool(path.stat().st_mode & stat.S_IXUSR)


def test_github_tree_mode_100755_survives_into_the_quarantined_files(tmp_path):
    """Every hub file used to land 0644, so ``scripts/run`` failed with "Permission denied"."""
    tree = [
        {"path": "skills/demo/SKILL.md", "type": "blob", "mode": "100644"},
        {"path": "skills/demo/scripts/run", "type": "blob", "mode": "100755"},
        {"path": "skills/demo/scripts/notes.txt", "type": "blob", "mode": "100644"},
        {"path": "skills/other/bin/tool", "type": "blob", "mode": "100755"},
    ]
    source = GitHubSource(auth=MagicMock(spec=GitHubAuth))
    with patch.object(source, "_get_repo_tree", return_value=("main", tree)), \
         patch.object(source, "_fetch_file_content", return_value="---\nname: demo\n---\n"), \
         patch.object(source, "_fetch_file_bytes", return_value=b"#!/bin/sh\necho ok\n"):
        bundle = source.fetch("owner/repo/skills/demo")

    assert bundle.executables == {"scripts/run"}
    q_path = _quarantine(tmp_path, bundle)
    assert _is_exec(q_path / "scripts" / "run")
    assert not _is_exec(q_path / "scripts" / "notes.txt")
    assert not _is_exec(q_path / "SKILL.md")


def test_local_optional_skill_keeps_its_executable_bit(tmp_path):
    from tools.skills_hub_official import OptionalSkillSource
    skill = tmp_path / "optional" / "cat" / "demo"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: demo\ndescription: d\n---\n", encoding="utf-8")
    (skill / "scripts" / "run").write_text("#!/bin/sh\n", encoding="utf-8")
    os.chmod(skill / "scripts" / "run", 0o755)
    source = OptionalSkillSource()
    source._optional_dir = tmp_path / "optional"

    bundle = source.fetch("official/cat/demo")

    assert bundle.executables == {"scripts/run"}
    assert _is_exec(_quarantine(tmp_path, bundle) / "scripts" / "run")

def test_mode_only_github_change_is_an_available_update(tmp_path):
    """A 100644 -> 100755 Git change must update an installed 0644 script, even with identical bytes."""
    import tools.skills_hub as hub
    from tools.skills_hub_install import bundle_content_hash, check_for_skill_updates
    from tools.skills_hub_models import SkillBundle

    skills_dir = tmp_path / "skills"
    installed = skills_dir / "demo"
    (installed / "scripts").mkdir(parents=True)
    skill_md = "---\nname: demo\n---\n"
    script_bytes = b"#!/bin/sh\necho ok\n"
    (installed / "SKILL.md").write_text(skill_md, encoding="utf-8")
    script_path = installed / "scripts" / "run"
    script_path.write_bytes(script_bytes)
    os.chmod(script_path, 0o644)

    bundle = SkillBundle(
        name="demo",
        files={"SKILL.md": skill_md, "scripts/run": script_bytes},
        source="github", identifier="owner/repo/skills/demo", trust_level="community",
        executables=frozenset({"scripts/run"}),
        metadata={"source_revision": "b" * 40},
    )
    lock = MagicMock()
    lock.list_installed.return_value = [{
        "name": "demo", "source": "github", "identifier": bundle.identifier,
        "install_path": "demo", "content_hash": bundle_content_hash(bundle),
        "metadata": {"source_revision": "a" * 40},
    }]
    source = MagicMock()
    source.source_id.return_value = "github"
    source.current_revision.return_value = "b" * 40
    source.fetch.return_value = bundle

    with patch.object(hub, "SKILLS_DIR", skills_dir):
        assert check_for_skill_updates(lock=lock, sources=[source])[0]["status"] == "update_available"
        os.chmod(script_path, 0o755)
        assert check_for_skill_updates(lock=lock, sources=[source])[0]["status"] == "up_to_date"
