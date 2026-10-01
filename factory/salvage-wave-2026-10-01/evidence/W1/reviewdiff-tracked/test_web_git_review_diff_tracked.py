"""review_diff (unstaged) must never render a tracked file as a new-file all-add.

An empty unstaged diff also means a clean or fully staged tracked file (e.g.
staged after the review list snapshot, so the row still says staged=False);
only a file git does not know yet gets the synthesized all-add, the same rule
file_diff_vs_head already follows. Python twin of the Electron reviewDiff test.
"""

import subprocess
from pathlib import Path

import pytest

from hermes_cli.web_git import review_diff


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def test_unstaged_review_diff_of_tracked_file_is_never_an_all_add(repo):
    # Pristine tracked file: nothing unstaged to show.
    assert review_diff(str(repo), "tracked.txt", "uncommitted", None, False) == ""

    # Fully staged after the list snapshot (stale staged=False).
    (repo / "tracked.txt").write_text("tracked\nstaged edit\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    assert review_diff(str(repo), "tracked.txt", "uncommitted", None, False) == ""


def test_unstaged_review_diff_still_all_adds_an_untracked_file(repo):
    (repo / "new.txt").write_text("fresh\n", encoding="utf-8")

    diff = review_diff(str(repo), "new.txt", "uncommitted", None, False)

    assert "new file mode" in diff
    assert "+fresh" in diff
