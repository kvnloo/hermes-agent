"""Block reason in the wake synth for blocked / block_loop_detected events.

Non-push (api_server) subscriptions receive ONLY the synthetic wake turn: the
text ping carrying ``⏸ … blocked: <reason>`` is skipped for them. Without the
reason in the synth the woken session learns that the task stopped but not
why. The reason is redacted with the same helper used for review feedback.
"""

import asyncio

from gateway.config import Platform
from hermes_cli import kanban_db as kb
from hermes_cli import kanban_db_connect as kbc
from hermes_cli import kanban_db_notify as kbn

from tests.gateway.test_kanban_notifier_apiserver_wake import (
    ApiServerLikeAdapter,
    _make_runner,
    _run_one_notifier_tick,
)


def _blocked_sub(reason, *, block_twice=False):
    conn = kbc.connect()
    try:
        tid = kb.create_task(conn, title="needs a decision", assignee="worker")
        kbn.add_notify_sub(conn, task_id=tid, platform="api_server", chat_id="bot-chat")
        kb.block_task(conn, tid, reason=reason, kind="needs_input")
        if block_twice:
            for _ in range(2):
                kb.unblock_task(conn, tid)
                kb.block_task(conn, tid, reason=reason, kind="needs_input")
        return tid
    finally:
        conn.close()


def _completed_sub():
    conn = kbc.connect()
    try:
        tid = kb.create_task(conn, title="finished", assignee="worker")
        kbn.add_notify_sub(conn, task_id=tid, platform="api_server", chat_id="bot-chat")
        kb.complete_task(conn, tid, summary="all done")
        return tid
    finally:
        conn.close()


def _wake_texts(tmp_path, monkeypatch, make):
    monkeypatch.setenv("HERMES_KANBAN_DB", str(tmp_path / "wake.db"))
    kb.init_db()
    make()
    posts = []

    async def fake_self_post(adapter, *, text, session_id, notification_category="result", profile=None):
        posts.append(text)

    import gateway.wake as wake_mod

    monkeypatch.setattr(wake_mod, "_self_post_chat_completion", fake_self_post)
    runner = _make_runner({Platform.API_SERVER: ApiServerLikeAdapter()})
    asyncio.run(_run_one_notifier_tick(monkeypatch, runner))
    return posts


def test_blocked_wake_carries_block_reason(tmp_path, monkeypatch):
    posts = _wake_texts(
        tmp_path, monkeypatch,
        lambda: _blocked_sub("Should the Queue page show a deferral hint, or stay API-only?"),
    )
    assert len(posts) == 1
    assert "Block reason: Should the Queue page show a deferral hint, or stay API-only?" in posts[0]


def test_blocked_wake_reason_is_redacted_and_bounded(tmp_path, monkeypatch):
    secret = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
    reason = f"token {secret} at /Users/someone/private/notes.txt " + "x" * 400
    posts = _wake_texts(tmp_path, monkeypatch, lambda: _blocked_sub(reason))
    assert len(posts) == 1
    line = next(ln for ln in posts[0].splitlines() if ln.startswith("Block reason: "))
    assert secret not in line
    assert "/Users/someone" not in line and "[local path]" in line
    assert len(line) <= len("Block reason: ") + 160
    assert line.endswith("…")


def test_block_loop_detected_wake_carries_block_reason(tmp_path, monkeypatch):
    posts = _wake_texts(
        tmp_path, monkeypatch,
        lambda: _blocked_sub("waiting on the operator to pick a mode", block_twice=True),
    )
    assert posts, "expected at least one wake"
    assert any("Block reason: waiting on the operator to pick a mode" in p for p in posts)


def test_non_block_wake_has_no_block_reason_line(tmp_path, monkeypatch):
    posts = _wake_texts(tmp_path, monkeypatch, _completed_sub)
    assert len(posts) == 1
    assert "Block reason:" not in posts[0]


def test_blocked_without_reason_adds_no_line(tmp_path, monkeypatch):
    posts = _wake_texts(tmp_path, monkeypatch, lambda: _blocked_sub(None))
    assert len(posts) == 1
    assert "Block reason:" not in posts[0]


def _gave_up_sub(error, *, force_trip=True, failure_limit=2, terminal_provider=False):
    conn = kbc.connect()
    try:
        tid = kb.create_task(conn, title="worker stopped", assignee="worker")
        kbn.add_notify_sub(conn, task_id=tid, platform="api_server", chat_id="bot-chat")
        # Simulate the dispatcher breaker: mark the task blocked, then emit the
        # single `gave_up` event that carries `error` and `failures` (no
        # separate `blocked` event follows to fill the wake detail slot).
        from hermes_cli import kanban_db_dispatch as kbd
        assert kbd._record_task_failure(
            conn, tid, error,
            outcome="crashed", failure_limit=failure_limit, force_trip=force_trip,
            release_claim=True, end_run=True,
            event_payload_extra={"terminal_provider": True} if terminal_provider else None,
        )
        return tid
    finally:
        conn.close()


def test_gave_up_wake_carries_error_as_block_reason(tmp_path, monkeypatch):
    posts = _wake_texts(
        tmp_path, monkeypatch,
        lambda: _gave_up_sub("spawn failed: ENOENT hermes"),
    )
    assert len(posts) == 1
    assert "Block reason: spawn failed: ENOENT hermes" in posts[0]


def test_terminal_provider_gave_up_wake_does_not_claim_retries_exhausted(tmp_path, monkeypatch):
    """A first-failure sticky trip (one of two attempts) must not claim retry exhaustion."""
    posts = _wake_texts(
        tmp_path, monkeypatch,
        lambda: _gave_up_sub(
            "the provider rejected this profile's credential",
            force_trip=True, failure_limit=2, terminal_provider=True,
        ),
    )
    assert len(posts) == 1
    assert "blocked; needs attention" in posts[0]
    assert "gave up (retries exhausted)" not in posts[0]
    assert "Block reason: the provider rejected this profile's credential" in posts[0]


def test_retry_budget_gave_up_wake_still_reports_exhaustion(tmp_path, monkeypatch):
    """A real threshold trip retains the more specific exhaustion status."""
    posts = _wake_texts(
        tmp_path, monkeypatch,
        lambda: _gave_up_sub("the worker crashed", force_trip=False, failure_limit=1),
    )
    assert len(posts) == 1
    assert "gave up (retries exhausted)" in posts[0]
    assert "Block reason: the worker crashed" in posts[0]
