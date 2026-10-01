"""A filtered `hermes sessions export` must not drop ended pinned sessions.

Pin is a "keep" flag for destructive bulk ops (prune/archive). A filtered
export is read-only, so it must select the same pinned rows that a bare
export and ``--session-id`` already include. Drives the real CLI parser and
a real on-disk SessionDB through every filtered export path.
"""

import json
import sys

import pytest

PLAIN = "20260101_000001_plain1"
PINNED = "20260101_000002_pinned"
PINNED_ARCHIVED = "20260101_000003_pinarc"
OTHER_SOURCE = "20260101_000004_tgram1"


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    import hermes_state
    from hermes_state import SessionDB

    db = SessionDB(tmp_path / "state.db")
    for sid, source in ((PLAIN, "cli"), (PINNED, "cli"), (PINNED_ARCHIVED, "cli"), (OTHER_SOURCE, "telegram")):
        db.create_session(session_id=sid, source=source, model="test-model")
        db.append_message(session_id=sid, role="user", content=f"hello from {sid}")
        db.append_message(session_id=sid, role="assistant", content="ok")
        db.end_session(sid, end_reason="user_exit")
    db.set_session_pinned(PINNED, True)
    db.set_session_pinned(PINNED_ARCHIVED, True)
    db.set_session_archived(PINNED_ARCHIVED, True)

    real_close = db.close
    monkeypatch.setattr(db, "close", lambda: None)  # the CLI closes its handle; keep ours for asserts
    monkeypatch.setattr(hermes_state, "SessionDB", lambda *a, **k: db)
    yield db
    real_close()


def _run_cli(monkeypatch, *argv):
    import hermes_cli.boot_bootstrap as boot_bootstrap
    import hermes_cli.main as main_mod

    # Keep the CLI entry point hermetic: no post-update home steps from a test.
    monkeypatch.setattr(boot_bootstrap, "maybe_run_boot_bootstrap", lambda *a, **k: None)
    monkeypatch.setattr(sys, "argv", ["hermes", "sessions", *argv])
    main_mod.main()


def _jsonl_ids(path):
    return {json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


@pytest.mark.parametrize("fmt", ["jsonl", "md"])
def test_filtered_export_writes_ended_pinned_and_pinned_archived_sessions(seeded_db, monkeypatch, tmp_path, fmt):
    if fmt == "jsonl":
        out = tmp_path / "backup.jsonl"
        _run_cli(monkeypatch, "export", "--source", "cli", "--format", "jsonl", str(out))
        exported = _jsonl_ids(out)
    else:
        out = tmp_path / "md-out"
        _run_cli(monkeypatch, "export", "--source", "cli", "--format", "md", str(out))
        manifest = out / "manifest.jsonl"
        exported = {json.loads(l)["session_id"] for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()}

    assert exported == {PLAIN, PINNED, PINNED_ARCHIVED}, f"filtered {fmt} export dropped pinned sessions"


@pytest.mark.parametrize("fmt", ["jsonl", "trace"])
def test_filtered_export_dry_run_counts_pinned_sessions(seeded_db, monkeypatch, tmp_path, capsys, fmt):
    _run_cli(monkeypatch, "export", "--source", "cli", "--format", fmt, "--dry-run", str(tmp_path / "x"))
    out = capsys.readouterr().out
    assert "Would export 3 session(s)" in out, out
    assert PINNED in out and PINNED_ARCHIVED in out


def test_prune_and_archive_still_spare_pinned_sessions(seeded_db):
    # The pin guard stays on for destructive selectors: only the export path opts out.
    assert {r["id"] for r in seeded_db.list_prune_candidates(source="cli", archived=None)} == {PLAIN}
    assert seeded_db.count_prune_matches(source="cli", archived=None) == 1
