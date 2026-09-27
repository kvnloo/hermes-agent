"""Revision-slot validation on the desktop review git routes.

``GET /api/git/review/diff`` and ``GET /api/git/review/list`` take a
client-supplied ``base`` query param that lands in git's revision slot
*before* any ``--`` fence. A leading-dash value is flag injection:
``--output=<path>`` turns the read-only ``git diff`` into an arbitrary
file write/truncate on the gateway host (``harden_git_argv`` only
inserts ``--no-ext-diff``; ``--output`` is honored regardless of
position). The desktop client always sends a commit SHA here, so the fix
fails closed on anything that is not one. ``review_rev_parse``'s ``ref``
may legitimately be a branch name, so only the flag-injection shape is
rejected there.
"""
import os
import subprocess

import pytest

from hermes_cli import web_git


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    subprocess.run(["git", "init", "-q"], cwd=r, env=env, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=r, env=env, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=r, env=env, check=True)
    (r / "code.py").write_text("print('v1')\n")
    subprocess.run(["git", "add", "-A"], cwd=r, env=env, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=r, env=env, check=True)
    return r


def _head_sha(repo) -> str:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


class TestReviewDiffBaseValidation:
    def test_diff_rejects_output_flag_injection(self, repo):
        victim = repo / "note.txt"
        victim.write_text("secret\n")
        with pytest.raises(RuntimeError, match="invalid base revision"):
            web_git.review_diff(str(repo), "code.py", "lastTurn", f"--output={victim}", False)
        # The victim file is byte-identical: no write happened.
        assert victim.read_text() == "secret\n"

    def test_diff_rejects_bare_dash_flag(self, repo):
        with pytest.raises(RuntimeError, match="invalid base revision"):
            web_git.review_diff(str(repo), "code.py", "lastTurn", "--stat", False)

    def test_diff_accepts_real_sha(self, repo):
        sha = _head_sha(repo)
        (repo / "code.py").write_text("print('v2')\n")
        diff = web_git.review_diff(str(repo), "code.py", "lastTurn", sha, False)
        assert "-print('v1')" in diff and "+print('v2')" in diff

    def test_diff_empty_base_still_returns_empty(self, repo):
        assert web_git.review_diff(str(repo), "code.py", "lastTurn", None, False) == ""
        assert web_git.review_diff(str(repo), "code.py", "lastTurn", "", False) == ""


class TestReviewListBaseValidation:
    def test_list_rejects_output_flag_injection(self, repo):
        victim = repo / "note.txt"
        victim.write_text("secret\n")
        with pytest.raises(RuntimeError, match="invalid base revision"):
            web_git.review_list(str(repo), "lastTurn", f"--output={victim}")
        assert victim.read_text() == "secret\n"

    def test_list_accepts_real_sha(self, repo):
        sha = _head_sha(repo)
        (repo / "code.py").write_text("print('v2')\n")
        result = web_git.review_list(str(repo), "lastTurn", sha)
        assert result["base"] == sha
        assert any(f["path"] == "code.py" for f in result["files"])


class TestReviewRevParseValidation:
    def test_rev_parse_rejects_leading_dash(self, repo):
        with pytest.raises(RuntimeError, match="invalid ref"):
            web_git.review_rev_parse(str(repo), "--show-toplevel")

    def test_rev_parse_accepts_branch_name(self, repo):
        assert web_git.review_rev_parse(str(repo), "HEAD") == _head_sha(repo)

    def test_rev_parse_none_still_resolves_head(self, repo):
        assert web_git.review_rev_parse(str(repo), None) == _head_sha(repo)
