"""A received move that is interrupted, partly fails, or meets edits made after it: what resume,
retry and undo may and may not do. Real files, a real ``state.db``, the real offline writer."""
import os
import shutil
import zipfile

import pytest

from hermes_cli import move_receive
from hermes_cli.move_sessions import OfflineSessions
from tests.hermes_cli.test_move_replace import _cloud, _laptop, _received
from hermes_cli.move_bundle import build_bundle


def test_a_swap_killed_mid_step_resumes_and_undo_still_brings_the_original_back(tmp_path, monkeypatch):
    cloud = _cloud(tmp_path)
    state = _received(tmp_path, cloud)
    real_move = shutil.move

    def killed(src, dst):  # the process dies right after the target's skill went into the snapshot
        real_move(src, dst)
        monkeypatch.setattr(shutil, "move", real_move)
        raise KeyboardInterrupt

    monkeypatch.setattr(shutil, "move", killed)
    with pytest.raises(KeyboardInterrupt):
        move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud), include={"skills"},
                           replace={"skills"})
    assert not (cloud / "skills" / "custom" / "shared").exists()

    state = move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert state["status"] == "applied", state
    assert "laptop copy" in (cloud / "skills" / "custom" / "shared" / "SKILL.md").read_text()
    state = move_receive.undo(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert state["status"] == "undone", state
    assert "cloud copy" in (cloud / "skills" / "custom" / "shared" / "SKILL.md").read_text()


def test_undo_touches_only_what_the_move_wrote_and_an_edit_since_blocks_it_until_retried(tmp_path):
    cloud = _cloud(tmp_path)
    state = _received(tmp_path, cloud)
    state = move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud), include={"memory"},
                               replace={"memory"})
    written = (cloud / "memories" / "MEMORY.md").read_text()
    (cloud / "config.yaml").write_text("display:\n  skin: chosen-after-the-move\n")
    (cloud / "memories" / "MEMORY.md").write_text("edited after the move")

    state = move_receive.undo(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert state["status"] == "undo_partial"
    assert state["result"]["undo_problems"] == ["changed since the move: memories/MEMORY.md"]
    assert (cloud / "memories" / "MEMORY.md").read_text() == "edited after the move"
    assert (cloud / "config.yaml").read_text() == "display:\n  skin: chosen-after-the-move\n"

    (cloud / "memories" / "MEMORY.md").write_text(written)
    state = move_receive.undo(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert state["status"] == "undone" and not state["result"]["undo_problems"], state
    assert (cloud / "memories" / "MEMORY.md").read_text() == "cloud fact\n"
    assert (cloud / "config.yaml").read_text() == "display:\n  skin: chosen-after-the-move\n"


def test_a_failed_conversation_keeps_the_move_partial_and_retryable_and_one_apply_runs_at_a_time(tmp_path):
    cloud = _cloud(tmp_path)
    good = tmp_path / "good.zip"
    build_bundle(_laptop(tmp_path), "default", good, include_history=True)
    bad = tmp_path / "move.zip"  # what _received uploads
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
        for name in src.namelist():
            dst.writestr(name, src.read(name))
        dst.writestr("sessions/zz-broken.json", "{not json")
    state = _received(tmp_path, cloud)
    move_dir = cloud / "moves" / state["id"]

    from pm.filesystem import lock_fd
    fd = os.open(move_dir / ".lock", os.O_CREAT | os.O_RDWR)
    try:
        assert lock_fd(fd, wait=False)
        with pytest.raises(move_receive.MoveError, match="already being applied") as refused:
            move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud), include={"sessions"})
        assert refused.value.status == 409
    finally:
        os.close(fd)

    state = move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud), include={"sessions"})
    step = state["steps"]["sessions"]
    assert state["status"] == "partial" and step["status"] == "partial", state
    assert step["imported"] == 1 and step["failed"] == 1 and step["errors"], step["errors"]
    assert (move_dir / "bundle.zip").is_file()
    again = move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert again["status"] == "partial" and again["steps"]["sessions"]["imported"] == 1


@pytest.mark.parametrize("replace", [False, True])
def test_undo_preserves_post_move_skill_edits(tmp_path, replace):
    """Undo must not silently discard edits made to an added OR replaced skill."""
    cloud = _cloud(tmp_path)
    skill = cloud / "skills" / "custom" / "shared" / "SKILL.md"
    if not replace:
        shutil.rmtree(skill.parent)
    state = _received(tmp_path, cloud)
    state = move_receive.apply(cloud, state["id"], sessions=OfflineSessions(cloud),
                               include={"skills"}, replace={"skills"} if replace else None)
    assert state["status"] == "applied", state
    moved = skill.read_bytes()
    skill.write_bytes(moved + b"\nuser edit after the move\n")

    undone = move_receive.undo(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert undone["status"] == "undo_partial", undone
    assert undone["result"]["undo_problems"] == ["changed since the move: skills/custom/shared"]
    assert skill.read_bytes() == moved + b"\nuser edit after the move\n"

    skill.write_bytes(moved)
    undone = move_receive.undo(cloud, state["id"], sessions=OfflineSessions(cloud))
    assert undone["status"] == "undone", undone
    if replace:
        assert "cloud copy" in skill.read_text()
    else:
        assert not skill.parent.exists()
