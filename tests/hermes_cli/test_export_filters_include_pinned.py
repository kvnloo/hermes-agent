"""Regression tests: filtered `sessions export` includes ended pinned sessions.

Before the fix, the export action block overrode the destructive ``archived``
default (``filters["archived"] = None``) but not the symmetric
``include_pinned`` default, so it inherited ``_prune_filter_where``'s
``include_pinned=False`` default and silently dropped every ended pinned
session from a filter-driven export — even though bare ``export``
(``export_all``) and ``export --session-id`` both include pinned rows.

Pinning is a destructive-op "keep" flag (it bounds prune/archive), not a
read-visibility flag. The fix sets ``filters["include_pinned"] = True`` in
the export branch so a filtered export is a read-only superset, consistent
with ``export_all`` and ``--session-id``.
"""

import json
import time
from argparse import Namespace

import pytest

import hermes_cli.sessions_cmd as sc
import hermes_state
from hermes_state import SessionDB

PINNED_ID = "20260101_000000_aaaaaa"
OTHER_ID = "20260101_000001_bbbbbb"
ARCHIVED_PINNED_ID = "20260101_000002_cccccc"


def _mk(db, sid, *, pinned=False, archived=False, source="cli"):
    """Create an ended, 100-day-old, 1-message session (export/prune eligible).

    The ``ended_at`` gate makes it a bulk-op candidate; the age makes
    ``--older-than`` unconstrained so the export count sees every row.
    """
    db.create_session(sid, source=source)
    with db._lock:
        old = time.time() - 100 * 86400
        db._conn.execute(
            "UPDATE sessions SET ended_at=?, started_at=?, "
            "message_count=1, archived=? WHERE id=?",
            (old, old, 1 if archived else 0, sid),
        )
        db._conn.commit()
    if pinned:
        db.set_session_pinned(sid, True)


def _export_args(output, *, source=None):
    """argparse.Namespace mirroring the ``sessions export`` subparser dests
    needed for the jsonl filter dispatch (see hermes_cli/main.py:14587+ and
    the export branch's ``_filter_arg_names`` in sessions_cmd.py:409-416)."""
    return Namespace(
        sessions_action="export",
        output=str(output),
        format="jsonl",
        session_id=None,
        dry_run=False,
        redact=False,
        only=None,
        source=source,
        older_than=None, newer_than=None, before=None, after=None,
        title=None, end_reason=None, cwd=None,
        min_messages=None, max_messages=None, model=None, provider=None,
        user=None, chat_id=None, chat_type=None, branch=None,
        min_tokens=None, max_tokens=None, min_cost=None, max_cost=None,
        min_tool_calls=None, max_tool_calls=None,
    )


def test_export_filter_dispatch_passes_include_pinned_and_archived_none(
    monkeypatch,
):
    """Through ``cmd_sessions``, a filtered jsonl export must pass
    ``include_pinned=True`` and ``archived=None`` to ``list_prune_candidates``
    — the kwargs signature of a read-only superset select. A regression that
    re-removes the ``include_pinned=True`` line fails this assertion."""
    seen = {}

    class FakeDB:
        def list_prune_candidates(self, **kwargs):
            seen.update(kwargs)
            return [{"id": "x", "source": "cli"}]

        def export_session(self, sid):
            return {"id": sid, "messages": []}

        def close(self):
            pass

    monkeypatch.setattr(hermes_state, "SessionDB", lambda: FakeDB())
    sc.cmd_sessions(_export_args("-", source="cli"), sessions_parser=None)
    assert seen.get("include_pinned") is True
    assert seen.get("archived") is None


def test_filtered_export_includes_ended_pinned_and_archived_pinned(
    tmp_path, monkeypatch,
):
    """End-to-end through ``cmd_sessions`` against a real on-disk ``SessionDB``:
    a filtered jsonl export (``--source cli``) must be a read-only superset that
    includes ended pinned rows AND ended pinned+archived rows (the
    ``archived=None`` + ``include_pinned=True`` overrides compose). Before the
    fix the pinned rows were silently dropped."""
    db = SessionDB(tmp_path / "state.db")
    _mk(db, PINNED_ID, pinned=True)
    _mk(db, OTHER_ID)
    _mk(db, ARCHIVED_PINNED_ID, pinned=True, archived=True)
    monkeypatch.setattr(hermes_state, "SessionDB", lambda: db)

    out = tmp_path / "backup.jsonl"
    try:
        sc.cmd_sessions(_export_args(out, source="cli"), sessions_parser=None)
        exported_ids = {
            json.loads(line)["id"]
            for line in out.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    finally:
        db.close()

    assert OTHER_ID in exported_ids
    assert PINNED_ID in exported_ids            # previously dropped (the bug)
    assert ARCHIVED_PINNED_ID in exported_ids   # archived=None + include_pinned=True
