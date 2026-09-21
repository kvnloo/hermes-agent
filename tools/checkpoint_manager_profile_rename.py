"""Rekey profile-local checkpoint projects after a named profile directory moves (#112973).

The checkpoint store lives under ``HERMES_HOME/checkpoints`` and therefore moves with a renamed
profile, but project identity inside it (ref, ``projects/<hash>.json``, agent-write ledger) is a
hash of the absolute workdir. Every workdir beneath the profile home gets a new hash after the
rename, so its history stays on disk yet unreachable from the new path until it is rekeyed here.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Dict

from tools import checkpoint_manager as cm

logger = logging.getLogger(__name__)


def _rebase_ledger_paths(ledger: Dict, old_workdir: Path, new_workdir: Path) -> Dict:
    """Move absolute ledger keys under ``old_workdir`` to the corresponding new path."""
    rebased = {}
    for raw_path, entry in ledger.items():
        try:
            relative = Path(raw_path).relative_to(old_workdir)
        except (TypeError, ValueError):
            rebased[raw_path] = entry
        else:
            rebased[str(new_workdir / relative)] = entry
    return rebased


def _rekey_project(store: Path, meta: Dict, old_workdir: Path, new_workdir: Path) -> None:
    """Install the project under its new hash, then drop the old identity.

    A retry (``hermes profile migrate-identity``) after a mid-way failure finds the new identity
    already populated, possibly with checkpoints taken under the new name since. Those must win:
    the new ref is only created when absent, and only when the surviving old tip is one of its
    ancestors do we drop the old identity and fold the old ledger under the new one. A new ref
    that does NOT descend from the old tip can only be the user's own continuing history —
    ``CheckpointManager._take`` seeded it as a parentless root commit because the first pass left
    ``new_ref`` absent (rename step 6 was skipped, or its ``update-ref new_ref -> old_tip`` failed);
    a genuine collision cannot occur because ``profiles/<new>`` must not exist for the rename to
    run (#112973 retry design). Re-parent that chain onto ``old_tip`` so the pre-rename history
    stays reachable from the new identity, then proceed to fold the old identity. If the
    ``update-ref`` that re-seeds ``new_ref`` fails after metadata/ledger were written, roll those
    back so a retry re-sees the pre-rekey state. The old metadata goes last because it keeps the
    project visible to the retry; the per-project git index is a rebuildable cache and is discarded.
    """
    old_hash, new_hash = meta["_hash"], cm._project_hash(str(new_workdir))
    old_ref, new_ref = cm._ref_name(old_hash), cm._ref_name(new_hash)
    old_tip = cm._ref_tip(store, str(new_workdir), old_ref)
    new_tip = cm._ref_tip(store, str(new_workdir), new_ref)
    if old_tip and new_tip:
        ok, _, _ = cm._run_git(["merge-base", "--is-ancestor", old_tip, new_tip], store, str(new_workdir),
                               allowed_returncodes={1})
        if not ok:
            # Re-parent the post-rename chain onto ``old_tip``: rebuild each of new_ref's commits
            # with ``old_tip`` as the root parent. No prior writes have happened yet in this call,
            # so on failure the caller (migrate_profile_checkpoint_projects) just warns and a retry
            # re-attempts cleanly. ``new_tip`` is refreshed so the ``if not new_tip`` re-seed below
            # is skipped and the existing fold/delete proceeds.
            new_chain = cm._ref_commits_oldest_first(store, str(new_workdir), new_ref)
            reparented_tip = cm._rebuild_linear_chain(store, str(new_workdir), new_chain, parent=old_tip) \
                if new_chain else None
            if not reparented_tip:
                raise OSError(f"could not re-parent {new_ref} onto {old_ref}")
            ok, _, err = cm._run_git(["update-ref", new_ref, reparented_tip], store, str(new_workdir))
            if not ok:
                raise OSError(f"could not re-parent {new_ref} onto {old_ref}: {err}")
            new_tip = reparented_tip
    meta_path = cm._project_meta_path(store, new_hash)
    new_meta_existed_before = meta_path.exists()
    if not new_meta_existed_before:
        new_meta = {k: v for k, v in meta.items() if k != "_hash"}
        new_meta.update({"workdir": str(new_workdir), **cm._volume_evidence(new_workdir)})
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(new_meta), encoding="utf-8")
    old_ledger_path = cm._ledger_path(store, old_hash)
    new_ledger_path = cm._ledger_path(store, new_hash)
    new_ledger_existed_before = new_ledger_path.exists()
    new_ledger_before = cm._load_ledger(store, new_hash) if new_ledger_existed_before else {}
    if old_ledger_path.exists():
        ledger = _rebase_ledger_paths(cm._load_ledger(store, old_hash), old_workdir, new_workdir)
        ledger.update(cm._load_ledger(store, new_hash))  # writes under the new name are newer
        cm._save_ledger(store, new_hash, ledger)
    if old_tip:
        if not new_tip:
            ok, _, err = cm._run_git(["update-ref", new_ref, old_tip], store, str(new_workdir))
            if not ok:
                # Roll back the meta/ledger writes done earlier in this call so the next retry
                # re-sees the pre-rekey state and can re-seed ``new_ref`` from ``old_tip`` cleanly.
                if not new_meta_existed_before:
                    cm._unlink_quiet(meta_path)
                if old_ledger_path.exists():
                    if new_ledger_existed_before:
                        cm._save_ledger(store, new_hash, new_ledger_before)
                    else:
                        cm._unlink_quiet(new_ledger_path)
                raise OSError(f"could not create {new_ref}: {err}")
        if not cm._delete_ref(store, old_ref):
            raise OSError(f"could not delete {old_ref}")
    cm._unlink_quiet(cm._project_meta_path(store, old_hash))
    cm._unlink_quiet(old_ledger_path)
    cm._unlink_quiet(cm._index_path(store, old_hash))


def migrate_profile_checkpoint_projects(old_profile_dir: Path, new_profile_dir: Path) -> Dict[str, int]:
    """Rekey checkpoint projects whose workdirs moved with a profile rename.

    Only workdirs beneath ``old_profile_dir`` are affected: an external workdir keeps its absolute
    path (and hash) even though the store holding its history moved. A workdir that no longer
    exists under the new profile dir did not move and keeps its (orphaned) identity.
    """
    old_root = cm._normalize_path(str(old_profile_dir))
    new_root = cm._normalize_path(str(new_profile_dir))
    store = cm._store_path(new_root / "checkpoints")
    result = {"scanned": 0, "migrated": 0, "errors": 0}
    if not cm._store_has_head(store):
        return result
    if shutil.which("git") is None:
        # Without git the ref cannot move; rekeying only the metadata would orphan the history.
        logger.warning("Cannot migrate checkpoint projects after profile rename: git not found")
        result["errors"] = 1
        return result
    for meta in cm._list_projects(store):
        result["scanned"] += 1
        old_workdir = cm._normalize_path(str(meta.get("workdir") or ""))
        if not meta.get("workdir") or not old_workdir.is_relative_to(old_root):
            continue
        new_workdir = new_root / old_workdir.relative_to(old_root)
        if not new_workdir.is_dir():
            continue
        try:
            _rekey_project(store, meta, old_workdir, new_workdir)
            result["migrated"] += 1
        except OSError as exc:
            result["errors"] += 1
            logger.warning("Cannot migrate checkpoint project %s -> %s after profile rename: %s",
                           old_workdir, new_workdir, exc)
    return result
