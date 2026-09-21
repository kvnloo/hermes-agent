"""Profile rename must preserve profile-local checkpoint history (#112973)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from hermes_cli.profile_identity import migrate_profile_identity
from hermes_cli.profiles import create_profile, get_profile_dir, rename_profile
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
import tools.checkpoint_manager as cm
from tools.checkpoint_manager import CheckpointManager
from tools.checkpoint_manager_profile_rename import _rekey_project


@pytest.fixture()
def profile_env(tmp_path, monkeypatch):
    """Isolate profile paths and the process-level Hermes root."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    default_home = tmp_path / ".hermes"
    default_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HERMES_HOME", str(default_home))
    return default_home


def test_rename_preserves_profile_local_checkpoint_history(profile_env, tmp_path):
    """A moved profile keeps rollback history under the moved workspace path.

    Checkpoint refs, project metadata, and the safe-restore ledger are keyed by the
    absolute workdir path. Renaming ``profiles/old`` to ``profiles/new`` moves the
    checkpoint store itself, but it also changes every profile-local workdir key.
    """
    old_dir = create_profile("oldname", no_alias=True)
    workdir = old_dir / "project"
    workdir.mkdir()
    outside = tmp_path / "outside-project"  # control: not under the profile dir, same store
    outside.mkdir()
    (outside / "keep.txt").write_text("v1\n", encoding="utf-8")
    (workdir / "pyproject.toml").write_text("[project]\nname = 'rename-checkpoint'\n", encoding="utf-8")
    tracked = workdir / "note.txt"
    tracked.write_text("before\n", encoding="utf-8")

    token = set_hermes_home_override(old_dir)
    try:
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert manager.ensure_checkpoint(str(workdir), "before profile rename") is True
        checkpoint_hash = manager.list_checkpoints(str(workdir))[0]["hash"]
        assert manager.ensure_checkpoint(str(outside), "outside profile") is True
        outside_hash = manager.list_checkpoints(str(outside))[0]["hash"]
        tracked.write_text("after\n", encoding="utf-8")
        manager.record_agent_write(str(tracked))
    finally:
        reset_hermes_home_override(token)

    with patch("hermes_cli.profiles.check_alias_collision", return_value="skip"), \
         patch("hermes_cli.profiles._live_default_multiplexer", return_value=False):
        new_dir = rename_profile("oldname", "newname")

    new_workdir = new_dir / "project"
    new_tracked = new_workdir / "note.txt"
    token = set_hermes_home_override(new_dir)
    try:
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        checkpoints = manager.list_checkpoints(str(new_workdir))
        assert [entry["hash"] for entry in checkpoints] == [checkpoint_hash]
        assert [entry["hash"] for entry in manager.list_checkpoints(str(outside))] == [outside_hash]

        project_paths = {entry["workdir"] for entry in manager.list_all_checkpoints()}
        assert str(new_workdir.resolve()) in project_paths
        assert str(workdir.resolve()) not in project_paths

        plan = manager.safe_restore_plan(str(new_workdir), checkpoint_hash)
        assert plan["success"] is True
        assert plan["restore"] == ["note.txt"]
        assert plan["skipped"] == []

        restored = manager.restore(str(new_workdir), checkpoint_hash, safe=True)
        assert restored["success"] is True
        assert new_tracked.read_text(encoding="utf-8") == "before\n"
    finally:
        reset_hermes_home_override(token)


def test_retry_after_partial_rekey_keeps_checkpoints_taken_under_new_name(profile_env):
    """``migrate-identity`` after a mid-way failure must not rewind history to the old tip.

    Between the failed rename and the retry the user keeps working under the new profile, so the
    new ref already carries checkpoints (and ledger entries) the old identity never saw.
    """
    old_dir = create_profile("oldname", no_alias=True)
    workdir = old_dir / "project"
    workdir.mkdir()
    (workdir / "pyproject.toml").write_text("[project]\nname = 'retry'\n", encoding="utf-8")
    note = workdir / "note.txt"
    note.write_text("v1\n", encoding="utf-8")

    token = set_hermes_home_override(old_dir)
    try:
        assert CheckpointManager(enabled=True, max_snapshots=5).ensure_checkpoint(str(workdir), "c1") is True
    finally:
        reset_hermes_home_override(token)

    with patch("hermes_cli.profiles.check_alias_collision", return_value="skip"), \
         patch("hermes_cli.profiles._live_default_multiplexer", return_value=False), \
         patch.object(cm, "_delete_ref", return_value=False):  # old ref survives: partial rekey
        new_dir = rename_profile("oldname", "newname")

    new_workdir = new_dir / "project"
    new_note = new_workdir / "note.txt"
    token = set_hermes_home_override(new_dir)
    try:
        new_note.write_text("v2\n", encoding="utf-8")
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert manager.ensure_checkpoint(str(new_workdir), "c2") is True
        manager.record_agent_write(str(new_note))
        before = [entry["hash"] for entry in manager.list_checkpoints(str(new_workdir))]
        assert len(before) == 2
        store = cm._store_path(new_dir / "checkpoints")
        ledger_before = cm._load_ledger(store, cm._project_hash(str(new_workdir)))

        assert migrate_profile_identity("oldname", "newname") is True

        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert [entry["hash"] for entry in manager.list_checkpoints(str(new_workdir))] == before
        assert cm._load_ledger(store, cm._project_hash(str(new_workdir))) == ledger_before
        assert cm._list_project_refs(store, str(new_workdir)) == [cm._ref_name(cm._project_hash(str(new_workdir)))]
    finally:
        reset_hermes_home_override(token)


def test_retry_after_skipped_step6_recovers_via_reparenting(profile_env, tmp_path, caplog):
    """``migrate-identity`` after a partial rename that skipped step 6 must re-parent the
    parentless post-rename root commit onto the old tip — not fail closed forever.

    The unexercised pre-fix branch: rename step 4 (or 5) raises *after* the directory move at
    step 2, so step 6 (``_rekey_project``) never runs and ``new_ref`` stays absent. The user's
    next checkpoint under the new name is then a parentless root commit, and the retry's
    ``git merge-base --is-ancestor old new`` fails — the fail-closed branch raised ``OSError``
    and the retry never converged (#112973). With the fix, the new chain is re-parented onto
    the old tip and the migration completes.
    """
    import logging

    old_dir = create_profile("oldname", no_alias=True)
    workdir = old_dir / "project"
    workdir.mkdir()
    (workdir / "pyproject.toml").write_text("[project]\nname = 'retry2'\n", encoding="utf-8")
    note = workdir / "note.txt"
    note.write_text("v1\n", encoding="utf-8")

    token = set_hermes_home_override(old_dir)
    try:
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert manager.ensure_checkpoint(str(workdir), "c1") is True
        manager.record_agent_write(str(note))
    finally:
        reset_hermes_home_override(token)

    old_hash = cm._project_hash(str(workdir))
    old_store = cm._store_path(old_dir / "checkpoints")
    c1 = cm._ref_tip(old_store, str(workdir), cm._ref_name(old_hash))
    assert c1 is not None

    # Step 4 of rename_profile raises AFTER the dir move at step 2, so step 6 (_rekey_project)
    # is skipped entirely — the documented retry is the only recovery.
    with patch("hermes_cli.profiles.check_alias_collision", return_value="skip"), \
         patch("hermes_cli.profiles._live_default_multiplexer", return_value=False), \
         patch("hermes_cli.profiles.remove_wrapper_script", side_effect=OSError("EROFS")):
        with pytest.raises(OSError):
            rename_profile("oldname", "newname")
    new_dir = get_profile_dir("newname")
    assert new_dir.is_dir()  # step 2 succeeded; the rename physically happened

    # User keeps working under the renamed profile, taking a checkpoint. The first pass left
    # new_ref absent (step 6 was skipped), so _take builds a parentless root commit c2.
    new_workdir = new_dir / "project"
    new_note = new_workdir / "note.txt"
    new_note.write_text("v2\n", encoding="utf-8")
    store = cm._store_path(new_dir / "checkpoints")
    token = set_hermes_home_override(new_dir)
    try:
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert manager.ensure_checkpoint(str(new_workdir), "c2") is True
        manager.record_agent_write(str(new_note))

        new_hash = cm._project_hash(str(new_workdir))
        new_ref, old_ref = cm._ref_name(new_hash), cm._ref_name(old_hash)
        c2 = cm._ref_tip(store, str(new_workdir), new_ref)

        # Bug precondition: c2 is a parentless root commit — _commit_tree_args was called with
        # parent=None because ref_tip(new_ref) was None after the skipped first pass.
        parents = cm._git_out(["log", "--format=%P", "-1", c2], store, str(new_workdir)).strip()
        assert parents == ""

        # The fix: the documented retry now converges via the re-parenting path, instead of
        # raising OSError("... does not descend from ...") on every attempt.
        with caplog.at_level(logging.WARNING, logger="tools.checkpoint_manager_profile_rename"):
            assert migrate_profile_identity("oldname", "newname") is True
        assert not any("does not descend from" in r.message for r in caplog.records)

        # new_ref points at a fresh re-parented tip whose parent is the old tip (c1); the
        # pre-rename history stays reachable from the new identity.
        reparented_tip = cm._ref_tip(store, str(new_workdir), new_ref)
        assert reparented_tip is not None and reparented_tip != c2
        parent_of_tip = cm._git_out(["rev-parse", f"{reparented_tip}^"],
                                    store, str(new_workdir)).strip()
        assert parent_of_tip == c1

        # /rollback history now includes BOTH the pre-rename and post-rename checkpoints.
        checkpoints = CheckpointManager(enabled=True, max_snapshots=5).list_checkpoints(str(new_workdir))
        hashes = {entry["hash"] for entry in checkpoints}
        assert reparented_tip in hashes and c1 in hashes

        # Old identity fully folded: ref deleted, meta + ledger + index removed.
        assert cm._list_project_refs(store, str(new_workdir)) == [new_ref]
        assert cm._ref_tip(store, str(new_workdir), old_ref) is None
        assert not cm._project_meta_path(store, old_hash).exists()
        assert not cm._ledger_path(store, old_hash).exists()

        # Ledger folded under the new identity: the old note.txt path was rebased to the new
        # workdir, and the new note.txt entry taken under the new name survives on top.
        new_ledger = cm._load_ledger(store, new_hash)
        assert str(new_note) in new_ledger

        # End-to-end smoke: safe-restore plans resolve for both pre-rename and post-rename tips.
        plan_post = manager.safe_restore_plan(str(new_workdir), reparented_tip)
        assert plan_post["success"] is True
        plan_pre = manager.safe_restore_plan(str(new_workdir), c1)
        assert plan_pre["success"] is True

        # Idempotent retry: nothing left to rekey, still succeeds (errors == 0).
        assert migrate_profile_identity("oldname", "newname") is True
        assert cm._list_project_refs(store, str(new_workdir)) == [new_ref]
    finally:
        reset_hermes_home_override(token)


def test_rekey_rolls_back_meta_and_ledger_when_update_ref_fails(profile_env, tmp_path):
    """When the ``update-ref new_ref -> old_tip`` re-seed fails (e.g. ENOSPC/EIO, packed-refs
    lock contention), ``_rekey_project`` must revert the meta/ledger writes done earlier in the
    same call so the next retry re-sees the pre-rekey state and can re-seed cleanly.
    """
    old_dir = create_profile("oldname", no_alias=True)
    workdir = old_dir / "project"
    workdir.mkdir()
    (workdir / "pyproject.toml").write_text("[project]\nname = 'rollback'\n", encoding="utf-8")
    note = workdir / "note.txt"
    note.write_text("v1\n", encoding="utf-8")

    token = set_hermes_home_override(old_dir)
    try:
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert manager.ensure_checkpoint(str(workdir), "c1") is True
        manager.record_agent_write(str(note))
    finally:
        reset_hermes_home_override(token)

    # Simulate the rename by moving the profile directory; the checkpoint store moves with it.
    new_dir = old_dir.parent / "newname"
    old_dir.rename(new_dir)
    new_workdir = new_dir / "project"
    store = cm._store_path(new_dir / "checkpoints")
    old_hash = cm._project_hash(str(workdir))
    new_hash = cm._project_hash(str(new_workdir))
    new_ref, old_ref = cm._ref_name(new_hash), cm._ref_name(old_hash)
    new_meta_path = cm._project_meta_path(store, new_hash)
    new_ledger_path = cm._ledger_path(store, new_hash)

    # Pre-rekey state the rollback must restore: no new identity on disk or in refs.
    assert not new_meta_path.exists()
    assert not new_ledger_path.exists()
    assert cm._ref_tip(store, str(new_workdir), new_ref) is None
    assert cm._ref_tip(store, str(new_workdir), old_ref) is not None

    # The rename flow drives _rekey_project with the surviving old meta dict from _list_projects.
    old_metas = cm._list_projects(store)
    assert [m["_hash"] for m in old_metas] == [old_hash]
    meta = old_metas[0]

    # Mock update-ref new_ref old_tip to fail (only the re-seed call). All other git ops (the
    # ref-tip rev-parses, the delete_ref, the eventual merge-base checks) run for real.
    original_run_git = cm._run_git

    def selective_run_git(args, *rest, **kw):
        if args and args[:2] == ["update-ref", new_ref]:
            return False, "", "mocked EIO"
        return original_run_git(args, *rest, **kw)

    with patch.object(cm, "_run_git", new=selective_run_git):
        with pytest.raises(OSError, match=r"could not create "):
            _rekey_project(store, meta, Path(str(workdir)), Path(str(new_workdir)))

    # Rollback: nothing of the new identity was left dangling.
    assert not new_meta_path.exists()
    assert not new_ledger_path.exists()
    assert cm._ref_tip(store, str(new_workdir), new_ref) is None
    # The old identity survived — still visible to the next retry, so a clean re-seed is possible.
    assert cm._ref_tip(store, str(new_workdir), old_ref) is not None
    assert cm._project_meta_path(store, old_hash).exists()
    assert cm._ledger_path(store, old_hash).exists()


def test_rekey_rollback_preserves_existing_new_ledger_writes(profile_env, tmp_path):
    """When the rolled-back ``update-ref`` re-seed fails, the new ledger's pre-rekey entries
    (user ``record_agent_write`` writes that landed under the new name before the retry) must
    survive — the rollback restores the pre-merge state, not an empty slate.
    """
    old_dir = create_profile("oldname", no_alias=True)
    workdir = old_dir / "project"
    workdir.mkdir()
    (workdir / "pyproject.toml").write_text("[project]\nname = 'rollback2'\n", encoding="utf-8")
    note = workdir / "note.txt"
    note.write_text("v1\n", encoding="utf-8")

    token = set_hermes_home_override(old_dir)
    try:
        manager = CheckpointManager(enabled=True, max_snapshots=5)
        assert manager.ensure_checkpoint(str(workdir), "c1") is True
        manager.record_agent_write(str(note))
    finally:
        reset_hermes_home_override(token)

    # Move the profile (simulating the rename) so the new identity does not yet have a ref tip.
    new_dir = old_dir.parent / "newname"
    old_dir.rename(new_dir)
    new_workdir = new_dir / "project"
    store = cm._store_path(new_dir / "checkpoints")
    old_hash = cm._project_hash(str(workdir))
    new_hash = cm._project_hash(str(new_workdir))
    new_ref = cm._ref_name(new_hash)
    new_ledger_path = cm._ledger_path(store, new_hash)

    # Pre-existing new-ledger entries (e.g. ``record_agent_write`` between passes) the rollback
    # must NOT wipe — they live at the new identity even though no checkpoint has been taken yet.
    pre_existing_new_ledger = {str(new_workdir / "scratch.txt"): {"sha256": "abc", "ts": 1}}
    cm._save_ledger(store, new_hash, dict(pre_existing_new_ledger))
    assert new_ledger_path.exists()

    meta = cm._list_projects(store)[0]
    original_run_git = cm._run_git

    def selective_run_git(args, *rest, **kw):
        if args and args[:2] == ["update-ref", new_ref]:
            return False, "", "mocked EIO"
        return original_run_git(args, *rest, **kw)

    with patch.object(cm, "_run_git", new=selective_run_git):
        with pytest.raises(OSError):
            _rekey_project(store, meta, Path(str(workdir)), Path(str(new_workdir)))

    # Rollback restored the pre-merge state, preserving the user's writes under the new name.
    assert cm._load_ledger(store, new_hash) == pre_existing_new_ledger
