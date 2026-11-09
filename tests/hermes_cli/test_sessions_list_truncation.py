"""``hermes sessions list`` tells the user when ``--limit`` cut the listing (#111989).

The cap is applied inside the SQL query, so the lister probes one row past it; the footer
must appear only when that probe row exists.
"""

from argparse import Namespace

import pytest

from hermes_cli import sessions_cmd


@pytest.fixture
def db(tmp_path):
    from hermes_state import SessionDB
    db = SessionDB(db_path=tmp_path / "state.db")
    for i in range(6):
        db.create_session(f"sess_{i}", "cli")
        db.append_message(f"sess_{i}", "user", f"hello {i}")
    yield db
    db.close()


def _list(db, limit, capsys):
    sessions_cmd._cmd_list(db, Namespace(limit=limit, source=None, workspace=None))
    return capsys.readouterr().out


def test_footer_when_more_sessions_than_limit(db, capsys):
    out = _list(db, 4, capsys)
    ids = [line.split()[-1] for line in out.splitlines() if line.startswith("hello")]
    assert len(ids) == 4  # the probe row is never rendered
    assert "--limit 8" in out


def test_no_footer_when_listing_fits(db, capsys):
    assert "more" not in _list(db, 6, capsys)  # exactly the limit
    assert "more" not in _list(db, 20, capsys)  # fewer than the limit


def test_cron_sessions_hidden_by_default_but_visible_when_source_is_explicit(db, capsys):
    """Cron runs stay out of the human list without losing direct inspection (#151484)."""
    db.create_session("cron_run", "cron")
    db.append_message("cron_run", "user", "cron-only content")

    sessions_cmd._cmd_list(db, Namespace(limit=20, source=None, workspace=None))
    default_listing = capsys.readouterr().out
    assert "hello 0" in default_listing
    assert "cron-only content" not in default_listing

    sessions_cmd._cmd_list(db, Namespace(limit=20, source="cron", workspace=None))
    cron_listing = capsys.readouterr().out
    assert "cron-only content" in cron_listing
    assert "hello 0" not in cron_listing
