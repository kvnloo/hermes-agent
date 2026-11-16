"""detect_code_skew() against a real git checkout, through the real fingerprint reader.

The unit tests in test_code_skew.py stub ``_fingerprint`` with strings; these pin the
``git:<ref>:<sha>`` shape the commit comparison parses, as the reader actually produces it.
"""
import subprocess

import pytest

from gateway import code_skew


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "mod.py").write_text("X = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "one")
    monkeypatch.setattr(code_skew, "_PROJECT_ROOT", root)
    monkeypatch.setattr(code_skew, "_boot_fingerprint", None)
    return root


def _boot():
    code_skew.record_boot_fingerprint()


def test_branch_switch_same_commit_is_not_skew(repo):
    _boot()
    _git(repo, "checkout", "-q", "-b", "other")
    assert code_skew.detect_code_skew() is None


def test_detached_then_reattached_same_commit_is_not_skew(repo):
    _git(repo, "checkout", "-q", "--detach")
    _boot()
    _git(repo, "checkout", "-q", "main")
    assert code_skew.detect_code_skew() is None


def test_real_code_change_is_skew(repo):
    _boot()
    (repo / "mod.py").write_text("X = 2\n")
    _git(repo, "commit", "-qam", "two")
    assert code_skew.detect_code_skew() is not None


def test_current_code_sha_is_the_commit(repo):
    # cron/scheduler.py compares this with gateway_state.json's code_sha (a commit SHA)
    assert code_skew.current_code_sha() == _git(repo, "rev-parse", "HEAD")
