"""Checkpoints honour the user's own git ignore rules (info/exclude + core.excludesFile)."""

import subprocess

from tools.checkpoint_manager import CheckpointManager


def test_rollback_leaves_user_git_excluded_files_alone(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    global_ignore = home / "global-ignore"
    global_ignore.write_text("*.secret\n")
    subprocess.run(["git", "config", "--global", "core.excludesFile", str(global_ignore)], check=True)

    proj = tmp_path / "proj"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=True)
    (proj / ".git" / "info" / "exclude").write_text("notes.local\n")
    files = {"app.py": "v1", "notes.local": "old", "keys.secret": "old"}
    for name, text in files.items():
        (proj / name).write_text(text)

    monkeypatch.setattr("tools.checkpoint_manager.CHECKPOINT_BASE", tmp_path / "checkpoints")
    mgr = CheckpointManager(enabled=True)
    mgr.new_turn()
    assert mgr.ensure_checkpoint(str(proj))
    first = mgr.list_checkpoints(str(proj))[0]["hash"]

    for name in files:
        (proj / name).write_text("new")
    assert mgr.restore(str(proj), first)["success"]

    assert (proj / "app.py").read_text() == "v1"
    # Excluded by the user's git config: never snapshotted, so never reverted.
    assert (proj / "notes.local").read_text() == "new"
    assert (proj / "keys.secret").read_text() == "new"


def test_rule_added_after_an_earlier_checkpoint_still_protects_the_file(tmp_path, monkeypatch):
    # Upgrade path: the file was snapshotted before the rule existed (or before this fix),
    # so it is already in the per-project index; `git add -A` keeps updating tracked paths.
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    proj = tmp_path / "proj"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=True)
    (proj / "app.py").write_text("v1")
    (proj / "notes.local").write_text("old")

    monkeypatch.setattr("tools.checkpoint_manager.CHECKPOINT_BASE", tmp_path / "checkpoints")
    mgr = CheckpointManager(enabled=True)
    mgr.new_turn()
    assert mgr.ensure_checkpoint(str(proj))
    first = mgr.list_checkpoints(str(proj))[0]["hash"]

    (proj / ".git" / "info" / "exclude").write_text("notes.local\n")
    (proj / "app.py").write_text("v2")
    (proj / "notes.local").write_text("new")
    mgr.new_turn()
    assert mgr.ensure_checkpoint(str(proj))
    assert mgr.restore(str(proj), first)["success"]

    assert (proj / "app.py").read_text() == "v1"
    assert (proj / "notes.local").read_text() == "new"
