"""Regression for NousResearch/hermes-agent#151126: multiplexed dispatch hook scope."""

from types import SimpleNamespace
from unittest.mock import Mock

from agent.secret_scope import (
    current_secret_scope,
    get_secret,
    reset_multiplex_context,
    set_multiplex_context,
)
from gateway import kanban_watchers_dispatcher as dispatcher
from hermes_cli import kanban_db, lifecycle


def test_dispatch_tick_hook_reads_profile_secret(monkeypatch, tmp_path):
    home = tmp_path / "profile"
    home.mkdir()
    (home / ".env").write_text("HOSS_DISPATCH_TOKEN=profile-only\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("HOSS_DISPATCH_TOKEN", raising=False)

    observed = []
    conn = Mock()
    monkeypatch.setattr(
        dispatcher, "_kbc", lambda: SimpleNamespace(connect=lambda *, board: conn)
    )

    def dispatch_once(_conn, **_kwargs):
        kanban_db._fire_dispatch_tick_hook(
            SimpleNamespace(skipped_locked=True), board="board"
        )
        return "dispatched"

    monkeypatch.setattr(dispatcher, "_kbd", lambda: SimpleNamespace(dispatch_once=dispatch_once))
    monkeypatch.setattr(lifecycle, "has_hook", lambda event: event == "on_kanban_dispatch_tick")

    def on_tick(event, **_payload):
        assert event == "on_kanban_dispatch_tick"
        observed.append(get_secret("HOSS_DISPATCH_TOKEN"))

    monkeypatch.setattr(lifecycle, "invoke_hook", on_tick)

    settings = dispatcher._DispatcherSettings(
        interval=60,
        max_spawn=0,
        max_in_progress=None,
        failure_limit=2,
        stale_timeout_seconds=0,
        reconcile_orphans=False,
        default_assignee=None,
        max_in_progress_per_profile=None,
    )
    tick = dispatcher._KanbanDispatcher(
        SimpleNamespace(kanban_db_path=lambda _slug: home / "kanban.db"), settings
    )

    token = set_multiplex_context(True)
    try:
        assert current_secret_scope() is None
        assert tick.tick_once_for_board("board") == "dispatched"
        assert observed == ["profile-only"]
        assert current_secret_scope() is None
    finally:
        reset_multiplex_context(token)
    conn.close.assert_called_once()
