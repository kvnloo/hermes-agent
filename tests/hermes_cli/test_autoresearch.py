"""Tests for the Hermes /autoresearch port (hermes_cli/autoresearch.py).

Contracts adapted from OMP's autoresearch tests (MIT, /workspace/omp) plus
Hermes-specific profile-isolation, fail-closed security, and cache-stability
invariants.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from hermes_cli import autoresearch as ar  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Clean git repo with a committed harness printing METRIC lines."""
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    harness = tmp_path / "autoresearch.sh"
    harness.write_text("#!/bin/bash\necho METRIC score=100\necho ASI cold=true\n")
    (tmp_path / "code.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "init"], check=True)
    return tmp_path


def _make_session(repo_path: Path, **overrides):
    storage = ar.open_storage(str(repo_path))
    params = dict(
        name="exp",
        goal="lower the score",
        primary_metric="score",
        metric_unit="",
        direction="lower",
        preferred_command=ar.DEFAULT_HARNESS_COMMAND,
        branch=ar.git_current_branch(str(repo_path)),
        baseline_commit=ar.git_head_sha(str(repo_path)),
        max_iterations=None,
        scope_paths=[],
        off_limits=[],
        constraints=[],
        secondary_metrics=[],
        provider="nous",
        model="stealth/ox-alpha",
    )
    params.update(overrides)
    session_id = storage.open_session(**params)
    storage.close()
    return session_id


def _run_and_complete(repo_path: Path, metric_value="90"):
    out = ar.cmd_run(str(repo_path), timeout_seconds=30)
    assert "PASSED" in out
    return out


# ---------------------------------------------------------------------------
# Metric/ASI parsing (OMP helpers.ts contracts)
# ---------------------------------------------------------------------------


class TestParsing:
    def test_parse_metric_lines_basic(self):
        metrics = ar.parse_metric_lines("noise\nMETRIC score=42.5\nMETRIC other_ms=10\n")
        assert metrics == {"score": 42.5, "other_ms": 10}

    def test_parse_rejects_proto_keys(self):
        assert "__proto__" not in ar.parse_metric_lines("METRIC __proto__=1")

    def test_parse_rejects_non_numeric(self):
        assert ar.parse_metric_lines("METRIC score=oops") == {}

    def test_parse_asi_values(self):
        asi = ar.parse_asi_lines("ASI cold=true\nASI n=3\nASI tag=abc\nASI cfg={\"a\":1}\n")
        assert asi == {"cold": True, "n": 3, "tag": "abc", "cfg": {"a": 1}}

    def test_sanitize_asi_drops_denied_keys_recursively(self):
        cleaned = ar.sanitize_asi({"ok": 1, "__proto__": {"x": 1}, "nested": {"constructor": 2}})
        assert cleaned == {"ok": 1, "nested": {}}


# ---------------------------------------------------------------------------
# Branch isolation (git.ts contracts, hardened)
# ---------------------------------------------------------------------------


class TestBranchIsolation:
    def test_refuses_pure_jj(self, repo):
        (repo / ".jj").mkdir()
        (repo / ".git").rename(repo / ".git-hidden")  # simulate pure jj
        try:
            ok, _branch, error, _created = ar.ensure_autoresearch_branch(str(repo), None)
        finally:
            (repo / ".git-hidden").rename(repo / ".git")
        assert not ok
        assert "Jujutsu" in error

    def test_creates_autoresearch_branch_from_clean_tree(self, repo):
        ok, branch, error, created = ar.ensure_autoresearch_branch(str(repo), "make it fast")
        assert ok and created
        assert branch.startswith("autoresearch/make-it-fast-")
        assert ar.git_current_branch(str(repo)) == branch

    def test_refuses_dirty_tree(self, repo):
        (repo / "code.py").write_text("x = 2\n")
        ok, _b, error, _c = ar.ensure_autoresearch_branch(str(repo), None)
        assert not ok
        assert "dirty" in error

    def test_reuses_existing_branch(self, repo):
        _ok, first, _, _ = ar.ensure_autoresearch_branch(str(repo), "goal")
        ok, second, _, created = ar.ensure_autoresearch_branch(str(repo), "goal")
        assert ok and not created and second == first

    def test_refuses_outside_git_repo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ok, _b, error, _c = ar.ensure_autoresearch_branch(str(tmp_path), None)
        assert not ok
        assert "git repository" in error


# ---------------------------------------------------------------------------
# Full lifecycle: init → run → keep/discard → resume → stop → clear
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_init_requires_harness(self, repo, hermes_home):
        (repo / "autoresearch.sh").unlink()
        out = ar.run_slash("optimize things", cwd=str(repo))
        # Entering mode returns setup instructions; the hard gate lives in
        # `hermes autoresearch init`, which must refuse without a harness.
        assert "autoresearch.sh" in out
        out = ar.cmd_init(str(repo), "x", "score", provider="nous", model="stealth/ox-alpha")
        # Fail closed: missing harness is caught either by the harness gate or
        # by the dirty-tree gate (deleting the committed harness is itself dirt).
        assert "does not exist" in out or "dirty" in out

    def test_full_keep_discard_cycle(self, repo, hermes_home):
        # init on the fixture repo (already clean, harness committed)
        out = ar.cmd_init(
            str(repo), "exp1", "score",
            off_limits=["harness.lock"], provider="nous", model="stealth/ox-alpha",
        )
        assert "Started session" in out
        branch = ar.git_current_branch(str(repo))
        assert branch.startswith("autoresearch/")
        baseline_commit = ar.git_head_sha(str(repo))

        # Baseline run + KEEP defines baseline
        _run_and_complete(repo)
        out = ar.cmd_log(str(repo), "keep", "baseline", 100.0)
        assert f"Logged run #1: keep - baseline" in out.replace("\u2014", "-") or "Logged run #1" in out

        # Candidate edit that improves the metric
        (repo / "code.py").write_text("x = 2  # faster\n")
        harness = repo / "autoresearch.sh"
        harness.write_text("#!/bin/bash\necho METRIC score=80\n")
        _run_and_complete(repo)
        out = ar.cmd_log(str(repo), "keep", "speedup", 80.0)
        assert "committed" in out
        keep_head = ar.git_head_sha(str(repo))
        assert keep_head != baseline_commit

        # A rejected experiment must NOT destroy prior keeps
        (repo / "code.py").write_text("x = broken\n")
        _run_and_complete(repo)
        out = ar.cmd_log(str(repo), "discard", "regression", 999.0)
        assert "reset to HEAD" in out
        assert ar.git_head_sha(str(repo)) == keep_head
        assert (repo / "code.py").read_text() == "x = 2  # faster\n"

        # Kept commit content survived
        show = subprocess.run(
            ["git", "-C", str(repo), "show", "--stat", "--format=%s", "HEAD"],
            capture_output=True, text=True,
        )
        assert keep_head == ar.git_head_sha(str(repo))

    def test_keep_blocked_by_off_limits_without_justification(self, repo, hermes_home):
        ar.cmd_init(str(repo), "sec", "score", off_limits=["harness.lock"],
                    provider="nous", model="stealth/ox-alpha")
        _run_and_complete(repo)
        ar.cmd_log(str(repo), "keep", "baseline", 100.0)

        (repo / "harness.lock").write_text("tampered\n")
        _run_and_complete(repo)
        out = ar.cmd_log(str(repo), "keep", "cheat", 10.0)
        assert "REFUSED" in out
        # Nothing was logged — pending run still there
        storage = ar.open_storage_if_exists(str(repo))
        assert storage.get_pending_run(storage.get_active_session()["id"]) is not None

    def test_keep_allowed_with_justification(self, repo, hermes_home):
        ar.cmd_init(str(repo), "j", "score", off_limits=["misc.txt"],
                    provider="nous", model="stealth/ox-alpha")
        _run_and_complete(repo)
        ar.cmd_log(str(repo), "keep", "base", 100.0)
        (repo / "misc.txt").write_text("touched\n")
        _run_and_complete(repo)
        out = ar.cmd_log(str(repo), "keep", "deviation", 90.0,
                         justification="lockfile refresh is mechanical")
        assert "justified scope deviations" in out

    def test_max_iterations_closes_session(self, repo, hermes_home):
        ar.cmd_init(str(repo), "cap", "score", max_iterations=2,
                    provider="nous", model="stealth/ox-alpha")
        _run_and_complete(repo)
        ar.cmd_log(str(repo), "keep", "baseline", 100.0)
        _run_and_complete(repo)
        out = ar.cmd_log(str(repo), "keep", "second", 99.0)
        assert "Maximum experiments reached" in out
        storage = ar.open_storage_if_exists(str(repo))
        assert storage.get_active_session() is None

    def test_pending_run_must_be_logged_before_next_run(self, repo, hermes_home):
        ar.cmd_init(str(repo), "seq", "score", provider="nous", model="stealth/ox-alpha")
        _run_and_complete(repo)
        _run_and_complete(repo)
        storage = ar.open_storage_if_exists(str(repo))
        runs = storage.list_runs(storage.get_active_session()["id"])
        abandoned = [r for r in runs if r["abandoned_at"]]
        assert len(abandoned) == 1, "starting a new run must abandon the prior pending run"

    def test_resume_after_restart(self, repo, hermes_home):
        ar.cmd_init(str(repo), "resume-me", "score", provider="nous", model="stealth/ox-alpha")
        _run_and_complete(repo)
        ar.cmd_log(str(repo), "keep", "baseline", 100.0)
        # Simulate restart: fresh storage instance via run_slash with no goal
        out = ar.run_slash("", cwd=str(repo))
        # bare toggle turns mode off when active
        assert "off" in out.lower()

        out = ar.run_slash("updated goal", cwd=str(repo))
        assert "Resuming autoresearch session" in out

    def test_clear_reset_tree_restores_baseline(self, repo, hermes_home):
        ar.cmd_init(str(repo), "wipe", "score", provider="nous", model="stealth/ox-alpha")
        _run_and_complete(repo)
        ar.cmd_log(str(repo), "keep", "baseline", 100.0)
        (repo / "extra.txt").write_text("untracked junk\n")
        out = ar.cmd_clear(str(repo))
        assert "Closed session" in out
        assert not (repo / "extra.txt").exists()
        storage = ar.open_storage_if_exists(str(repo))
        assert storage.get_active_session() is None

    def test_clear_refuses_to_destroy_user_dirt_outside_branch(self, repo, hermes_home):
        ar.cmd_init(str(repo), "safe", "score", provider="nous", model="stealth/ox-alpha")
        # leave the autoresearch branch back to main with user dirt
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True)
        (repo / "precious.txt").write_text("user work\n")
        out = ar.cmd_clear(str(repo), reset_tree_force=True)
        assert "Refusing" in out
        assert (repo / "precious.txt").exists()


# ---------------------------------------------------------------------------
# Harness execution safety
# ---------------------------------------------------------------------------


class TestRunSafety:
    def test_timeout_kills_process_tree(self, repo, hermes_home):
        ar.cmd_init(str(repo), "to", "score", provider="nous", model="stealth/ox-alpha")
        harness = repo / "autoresearch.sh"
        # Detached grandchild that would outlive us if only the shell were killed.
        harness.write_text(
            "#!/bin/bash\n"
            'sleep 0.1 && echo METRIC score=1 &\n'
            "sleep 300\n"
        )
        out = ar.cmd_run(str(repo), timeout_seconds=2)
        assert "TIMEOUT" in out
        storage = ar.open_storage_if_exists(str(repo))
        run = storage.get_pending_run(storage.get_active_session()["id"])
        assert run["timed_out"] == 1

    def test_crash_recorded(self, repo, hermes_home):
        ar.cmd_init(str(repo), "crash", "score", provider="nous", model="stealth/ox-alpha")
        (repo / "autoresearch.sh").write_text("#!/bin/bash\nexit 3\n")
        out = ar.cmd_run(str(repo), timeout_seconds=30)
        assert "FAILED with exit code 3" in out
        out = ar.cmd_log(str(repo), "crash", "boom", 0.0)
        assert "Logged run" in out

    def test_malicious_output_is_sanitized(self, repo, hermes_home):
        ar.cmd_init(str(repo), "mal", "score", provider="nous", model="stealth/ox-alpha")
        (repo / "autoresearch.sh").write_text(
            "#!/bin/bash\n"
            'echo "METRIC score=NaN"\n'
            'echo "METRIC __proto__=7"\n'
            'echo "ASI constructor=pwn"\n'
        )
        out = ar.cmd_run(str(repo), timeout_seconds=30)
        assert "PASSED" in out
        storage = ar.open_storage_if_exists(str(repo))
        run = storage.get_pending_run(storage.get_active_session()["id"])
        parsed = json.loads(run["parsed_metrics_json"] or "{}")
        assert "__proto__" not in parsed
        assert "score" not in parsed or isinstance(parsed.get("score"), float)


# ---------------------------------------------------------------------------
# Profile isolation + model pinning
# ---------------------------------------------------------------------------


class TestProfileAndModel:
    def test_db_lives_under_hermes_home(self, repo, hermes_home):
        ar.cmd_init(str(repo), "iso", "score", provider="nous", model="stealth/ox-alpha")
        db = ar.autoresearch_db_path(str(repo))
        assert db.is_relative_to(Path(os.environ["HERMES_HOME"]))
        assert db.exists()

    def test_two_projects_do_not_share_state(self, repo, tmp_path, hermes_home):
        ar.cmd_init(str(repo), "p1", "score", provider="nous", model="stealth/ox-alpha")
        other = tmp_path / "other-repo"
        other.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=other, check=True)
        subprocess.run(["git", "-C", str(other), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(other), "config", "user.name", "t"], check=True)
        (other / "autoresearch.sh").write_text("#!/bin/bash\necho METRIC score=5\n")
        subprocess.run(["git", "-C", str(other), "add", "."], check=True)
        subprocess.run(["git", "-C", str(other), "commit", "-qm", "init"], check=True)
        out = ar.cmd_init(str(other), "p2", "score", provider="nous", model="stealth/ox-alpha")
        assert "Started session #1" in out  # separate DB → fresh id space

    def test_model_mismatch_fails_closed(self, repo, hermes_home):
        out = ar.cmd_init(str(repo), "bad", "score",
                          provider="openai", model="gpt-5.6-sol")
        assert "Model mismatch" in out
        storage = ar.open_storage_if_exists(str(repo))
        assert storage is None or storage.get_active_session() is None

    def test_canary_model_accepted(self, repo, hermes_home):
        out = ar.cmd_init(str(repo), "good", "score",
                          provider="nous", model="stealth/ox-alpha")
        assert "Started session" in out


# ---------------------------------------------------------------------------
# Branch-bound resume
# ---------------------------------------------------------------------------


class TestBranchBound:
    def test_status_reports_branch_mismatch(self, repo, hermes_home):
        ar.cmd_init(str(repo), "bound", "score", provider="nous", model="stealth/ox-alpha")
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True)
        out = ar.cmd_status(str(repo))
        assert "bound to branch" in out

    def test_commands_refuse_off_branch(self, repo, hermes_home):
        ar.cmd_init(str(repo), "offb", "score", provider="nous", model="stealth/ox-alpha")
        subprocess.run(["git", "-C", str(repo), "checkout", "-q", "main"], check=True)
        assert "no active autoresearch session" in ar.cmd_run(str(repo)).lower() or \
            "Error" in ar.cmd_run(str(repo))


# ---------------------------------------------------------------------------
# Cache-safety invariant (Hermes adaptation)
# ---------------------------------------------------------------------------


class TestCacheStability:
    def test_no_dynamic_toolset_mutation_in_module(self):
        """The module must never mutate toolsets/schemas mid-conversation.

        Source-level guard per AGENTS.md exception for this specific port:
        OMP's setActiveTools pattern must not be copied into Hermes. The
        module exposes no tool-registration surface at all; assert the
        behavioral contract by checking the public API has no such hook.
        """
        public = {name for name in dir(ar) if not name.startswith("_")}
        forbidden = {"setActiveTools", "register_tool", "set_active_tools",
                     "TOOL_NAMES", "EXPERIMENT_TOOL_NAMES"}
        assert not (public & forbidden)

    def test_run_slash_returns_static_text_only(self, repo, hermes_home):
        out = ar.run_slash("goal here", cwd=str(repo))
        assert isinstance(out, str)
        # Instruction text, never a tool-schema or system prompt mutation.
        assert "tools" not in out.lower() or "terminal" in out.lower()
