"""Project isolation for the shared v2 checkpoint store.

The store is one git object DB for every project (``refs/hermes/<hash16>``
per project).  Mere object existence (``git cat-file -t``) must not make a
hash a valid restore/diff target for a different directory: restore and
diff must only accept commits reachable from that directory's own ref.
Separately, ``ensure_checkpoint`` must never snapshot the checkpoint
infrastructure itself.
"""
from pathlib import Path

import pytest

from tools.checkpoint_manager import CheckpointManager


@pytest.fixture()
def checkpoint_base(tmp_path, monkeypatch):
    base = tmp_path / "checkpoints"
    monkeypatch.setattr("tools.checkpoint_manager.CHECKPOINT_BASE", base)
    return base


@pytest.fixture()
def two_projects(tmp_path):
    proj_a = tmp_path / "projA"
    proj_a.mkdir()
    (proj_a / "alpha.txt").write_text("alpha content\n")
    proj_b = tmp_path / "projB"
    proj_b.mkdir()
    (proj_b / "beta.txt").write_text("beta content\n")
    return proj_a, proj_b


@pytest.fixture()
def checkpointed(two_projects, checkpoint_base):
    proj_a, proj_b = two_projects
    mgr = CheckpointManager(enabled=True, max_snapshots=50)
    assert mgr.ensure_checkpoint(str(proj_a)) is True
    assert mgr.ensure_checkpoint(str(proj_b)) is True
    hash_b = mgr.list_checkpoints(str(proj_b))[0]["hash"]
    hash_a = mgr.list_checkpoints(str(proj_a))[0]["hash"]
    return mgr, proj_a, proj_b, hash_a, hash_b


class TestCrossProjectRestore:
    def test_restore_rejects_foreign_checkpoint(self, checkpointed):
        mgr, proj_a, proj_b, _, hash_b = checkpointed
        result = mgr.restore(str(proj_a), hash_b)
        assert result["success"] is False
        assert "not a checkpoint of this directory" in result["error"]
        # Project A's tree is byte-identical: no foreign files materialized.
        assert (proj_a / "alpha.txt").read_text() == "alpha content\n"
        assert not (proj_a / "beta.txt").exists()
        assert sorted(p.name for p in proj_a.iterdir()) == ["alpha.txt"]

    def test_diff_rejects_foreign_checkpoint(self, checkpointed):
        mgr, proj_a, _, _, hash_b = checkpointed
        result = mgr.diff(str(proj_a), hash_b)
        assert result["success"] is False
        assert "not a checkpoint of this directory" in result["error"]

    def test_safe_restore_plan_rejects_foreign_checkpoint(self, checkpointed):
        mgr, proj_a, _, _, hash_b = checkpointed
        plan = mgr._safe_restore_plan(str(proj_a), hash_b)
        assert plan["success"] is False
        assert "not a checkpoint of this directory" in plan["error"]

    def test_safe_restore_rejects_foreign_checkpoint(self, checkpointed):
        mgr, proj_a, _, _, hash_b = checkpointed
        result = mgr.restore(str(proj_a), hash_b, safe=True)
        assert result["success"] is False
        assert "not a checkpoint of this directory" in result["error"]
        assert not (proj_a / "beta.txt").exists()

    def test_restore_accepts_own_checkpoint(self, checkpointed):
        mgr, proj_a, _, hash_a, _ = checkpointed
        (proj_a / "alpha.txt").write_text("alpha modified\n")
        result = mgr.restore(str(proj_a), hash_a)
        assert result["success"] is True
        assert (proj_a / "alpha.txt").read_text() == "alpha content\n"

    def test_diff_accepts_own_checkpoint(self, checkpointed):
        mgr, proj_a, _, hash_a, _ = checkpointed
        (proj_a / "alpha.txt").write_text("alpha modified\n")
        result = mgr.diff(str(proj_a), hash_a)
        assert result["success"] is True


class TestStoreSelfSnapshot:
    def test_ensure_checkpoint_skips_checkpoint_base(self, tmp_path, checkpoint_base):
        mgr = CheckpointManager(enabled=True, max_snapshots=50)
        assert mgr.ensure_checkpoint(str(checkpoint_base)) is False
        # No project entry was created for the infrastructure dir.
        assert mgr.list_checkpoints(str(checkpoint_base)) == []

    def test_ensure_checkpoint_skips_store_dir_itself(self, checkpoint_base):
        mgr = CheckpointManager(enabled=True, max_snapshots=50)
        assert mgr.ensure_checkpoint(str(checkpoint_base / "store")) is False

    def test_ensure_checkpoint_still_works_for_normal_project(
        self, tmp_path, checkpoint_base
    ):
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "main.py").write_text("print('hi')\n")
        mgr = CheckpointManager(enabled=True, max_snapshots=50)
        assert mgr.ensure_checkpoint(str(proj)) is True
        assert len(mgr.list_checkpoints(str(proj))) == 1
