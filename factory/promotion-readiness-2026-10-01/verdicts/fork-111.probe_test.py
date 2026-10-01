"""Probe for fork #111 (not for commit)."""
from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.profile_identity import migrate_profile_identity
from hermes_cli.profiles import create_profile, get_profile_dir, rename_profile
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
import tools.checkpoint_manager as cm
from tools.checkpoint_manager import CheckpointManager
from tools import checkpoint_maintenance as maintenance


@pytest.fixture()
def profile_env(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    default_home = tmp_path / ".hermes"
    default_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(default_home))
    return default_home


def _seed(old_dir, n=1):
    workdir = old_dir / "project"
    workdir.mkdir()
    (workdir / "pyproject.toml").write_text("[project]\nname = 'p'\n", encoding="utf-8")
    note = workdir / "note.txt"
    token = set_hermes_home_override(old_dir)
    try:
        m = CheckpointManager(enabled=True, max_snapshots=5)
        for i in range(n):
            note.write_text(f"old{i}\n", encoding="utf-8")
            m.new_turn()
            assert m.ensure_checkpoint(str(workdir), f"old{i}") is True
    finally:
        reset_hermes_home_override(token)
    return workdir


def _reasons(new_dir, new_workdir, max_snapshots=5):
    token = set_hermes_home_override(new_dir)
    try:
        return [e["reason"] for e in CheckpointManager(enabled=True, max_snapshots=max_snapshots).list_checkpoints(str(new_workdir))]
    finally:
        reset_hermes_home_override(token)


def test_A_skipped_rekey_then_checkpoint_then_retry(profile_env):
    old_dir = create_profile("oldname", no_alias=True)
    _seed(old_dir, n=2)
    with patch("hermes_cli.profiles.check_alias_collision", return_value="skip"), \
         patch("hermes_cli.profiles._live_default_multiplexer", return_value=False), \
         patch("hermes_cli.profiles.remove_wrapper_script", side_effect=OSError("EROFS")):
        with pytest.raises(OSError):
            rename_profile("oldname", "newname")
    new_dir = get_profile_dir("newname")
    new_workdir = new_dir / "project"
    token = set_hermes_home_override(new_dir)
    try:
        (new_workdir / "note.txt").write_text("new\n", encoding="utf-8")
        m = CheckpointManager(enabled=True, max_snapshots=5)
        assert m.ensure_checkpoint(str(new_workdir), "new0") is True
    finally:
        reset_hermes_home_override(token)
    print("before retry:", _reasons(new_dir, new_workdir))
    ok = migrate_profile_identity("oldname", "newname")
    print("retry ok:", ok, "after:", _reasons(new_dir, new_workdir))
    assert ok is True
    assert _reasons(new_dir, new_workdir) == ["new0", "old1", "old0"]


def test_B_partial_rekey_then_trim_then_retry(profile_env):
    """Upstream's own partial-rekey scenario, plus a take-path count trim before the retry."""
    old_dir = create_profile("oldname", no_alias=True)
    _seed(old_dir, n=2)
    with patch("hermes_cli.profiles.check_alias_collision", return_value="skip"), \
         patch("hermes_cli.profiles._live_default_multiplexer", return_value=False), \
         patch.object(maintenance, "_delete_ref", return_value=False):
        new_dir = rename_profile("oldname", "newname")
    new_workdir = new_dir / "project"
    token = set_hermes_home_override(new_dir)
    try:
        m = CheckpointManager(enabled=True, max_snapshots=2)
        (new_workdir / "note.txt").write_text("new0\n", encoding="utf-8")
        m.new_turn()
        assert m.ensure_checkpoint(str(new_workdir), "new0") is True
    finally:
        reset_hermes_home_override(token)
    before = _reasons(new_dir, new_workdir)
    print("before retry:", before)
    ok = migrate_profile_identity("oldname", "newname")
    after = _reasons(new_dir, new_workdir)
    print("retry ok:", ok, "after:", after)
    assert ok is True
    assert after == before
