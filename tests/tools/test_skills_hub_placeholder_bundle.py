"""A prose directory placeholder must not reject a GitHub skill bundle (#134628).

Integration coverage for liuhao1024's extractor fix in upstream PR #134646.
"""

from unittest.mock import MagicMock, patch

from tools.skills_hub_github import GitHubAuth, GitHubSource


def test_placeholder_directory_does_not_reject_github_skill_bundle():
    skill_md = (
        "---\nname: demo\ndescription: demo\n---\n"
        "Read `references/doc-types/<値>.md` or `references/doc-types/` "
        "and [overview](references/doc-types/overview.md).\n"
    )
    tree_entries = [
        {"path": "skills/demo/SKILL.md", "type": "blob", "mode": "100644"},
        {"path": "skills/demo/references/doc-types", "type": "tree", "mode": "040000"},
        {"path": "skills/demo/references/doc-types/overview.md", "type": "blob", "mode": "100644"},
    ]
    source = GitHubSource(auth=MagicMock(spec=GitHubAuth))
    with (
        patch.object(source, "_get_repo_tree", return_value=("main", tree_entries)),
        patch.object(source, "_fetch_file_content", return_value=skill_md),
        patch.object(source, "_fetch_file_bytes", return_value=b"overview"),
    ):
        bundle = source.fetch("owner/repo/skills/demo")

    assert bundle is not None
    assert bundle.files["references/doc-types/overview.md"] == b"overview"
