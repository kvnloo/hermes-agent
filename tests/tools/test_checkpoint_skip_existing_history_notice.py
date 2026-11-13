"""A skipped later snapshot must not erase earlier rollback history (#154876)."""

from tools import checkpoint_maintenance as maint
from tools import checkpoint_manager as cm


def test_doctor_notice_preserves_older_rollback_points(tmp_path, monkeypatch):
    workdir = tmp_path / "project"
    workdir.mkdir()
    source = workdir / "example.py"
    source.write_text("value = 1\n", encoding="utf-8")

    base = tmp_path / "checkpoints"
    monkeypatch.setattr(cm, "CHECKPOINT_BASE", base)
    manager = cm.CheckpointManager(enabled=True)

    assert manager.ensure_checkpoint(str(workdir), "before cap") is True
    assert maint.store_status(base)["projects"][0]["commits"] == 1

    manager.new_turn()
    source.write_text("value = 2\n", encoding="utf-8")
    # Exercise the real default cap, without creating 50,001 files.
    monkeypatch.setattr(cm, "_dir_file_count", lambda _: cm._MAX_FILES + 1)
    assert manager.ensure_checkpoint(str(workdir), "after cap") is False

    assert maint.store_status(base)["projects"][0]["commits"] == 1
    notice = maint.skipped_projects_notice()
    assert notice is not None
    assert f"file_count>{cm._MAX_FILES}" in notice
    assert "earlier snapshots, if any, remain available" in notice
    assert "No rollback point is kept there" not in notice
