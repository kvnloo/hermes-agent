"""Class-4 fix (handoff-context-rot): origin-tag filters prevent runtime notices
from being quoted as the owner's ask in handoff capsules.

The structural fix tags every user-role row with its origin when written
(kanban_goal_continuation, auto_continue, model_switch, etc.) and makes all
capsule/user-ask extraction paths filter on that tag instead of a deny-list
of text prefixes.
"""
from __future__ import annotations

from unittest.mock import patch

from agent.context_compressor import ContextCompressor
from agent.conversation_compression import _is_real_user_message
from hermes_cli.goals import KANBAN_GOAL_CONTINUATION_TEMPLATE


def _make_compressor():
    with patch("agent.context_compressor.get_model_context_length", return_value=100000):
        return ContextCompressor(model="test", quiet_mode=True)


def test_kanban_goal_continuation_notice_tagged_and_filtered():
    """A kanban goal continuation notice tagged with display_kind is skipped
    by the deterministic 'User asked' extractor, which falls back to the
    genuine owner ask.
    """
    c = _make_compressor()

    # The actual notice template used by the kanban goal loop.
    notice = KANBAN_GOAL_CONTINUATION_TEMPLATE.format(
        reason="still have open tests"
    )

    messages = [
        {"role": "user", "content": "fix the login bug on prod"},
        {"role": "assistant", "content": "on it"},
        # The notice arrives as the newest user turn, but it is tagged at
        # write time so it reads as a timeline event, never as Kevin's words.
        {
            "role": "user",
            "content": notice,
            "display_kind": "kanban_goal_continuation",
        },
    ]

    # _latest_user_task_snapshot must skip the notice and anchor on the real ask.
    snapshot = c._latest_user_task_snapshot(messages)
    assert snapshot is not None
    assert "fix the login bug on prod" in snapshot
    assert "Continuing toward this kanban task" not in snapshot


def test_kanban_goal_continuation_wrapped_in_still_in_progress():
    """When the notice is wrapped in the compactor's '[STILL IN PROGRESS ...
    do not start over.]' restatement header, the origin tag still wins.
    """
    c = _make_compressor()

    notice = KANBAN_GOAL_CONTINUATION_TEMPLATE.format(reason="open follow-ups")
    # The restatement header the compactor prepends when replaying an in-flight
    # task. The notice itself is the payload; the header is the frame.
    wrapped = "[STILL IN PROGRESS — this is the active request, restated after the compaction boundary because it was not finished yet. Continue it; do not start over.]\n" + notice

    messages = [
        {"role": "user", "content": "refactor the auth module"},
        {"role": "assistant", "content": "started"},
        {"role": "user", "content": wrapped, "display_kind": "kanban_goal_continuation"},
    ]

    snapshot = c._latest_user_task_snapshot(messages)
    assert snapshot is not None
    assert "refactor the auth module" in snapshot
    assert "Continuing toward this kanban task" not in snapshot
    assert "STILL IN PROGRESS" not in snapshot


def test_untagged_notice_still_filtered_by_legacy_prefixes():
    """The legacy content-prefix fallback catches the notices it already
    enumerates. On main the kanban goal-continuation template is NOT in that
    list (that is the class-4 gap the origin tag closes) — so this test
    documents the boundary rather than asserting coverage of every notice.
    """
    # These prefixes ARE in _SYNTHETIC_USER_PREFIXES on main; an untagged row
    # with one of them is still filtered.
    assert not _is_real_user_message(
        {"role": "user", "content": "[IMPORTANT: Background process done]"}
    )
    assert not _is_real_user_message(
        {"role": "user", "content": "[System: Your previous response was truncated]"}
    )


def test_kanban_notice_untagged_is_the_gap():
    """Document the gap the origin tag closes: on main the kanban goal
    continuation template has no legacy prefix, so an untagged copy reads as
    a real user turn. The tag makes it impossible instead of patching it.
    """
    notice = KANBAN_GOAL_CONTINUATION_TEMPLATE.format(reason="open follow-ups")
    assert _is_real_user_message(
        {"role": "user", "content": notice}
    ), "untagged kanban notice is the class-4 gap; the tag is the fix"
    # And with the tag, it is filtered — the structural guarantee.
    assert not _is_real_user_message(
        {"role": "user", "content": notice, "display_kind": "kanban_goal_continuation"}
    )


def test_real_user_turn_untagged():
    """A genuine owner turn has no display_kind and is not synthetic."""
    assert _is_real_user_message({"role": "user", "content": "please review the PR"})
    assert _is_real_user_message(
        {"role": "user", "content": "fix the login bug on prod"}
    )


def test_goal_loop_call_site_passes_tag():
    """The kanban goal loop's _run_turn must thread persist_user_display_kind
    so the persisted row carries the origin tag.
    """
    import cli

    import inspect

    src = inspect.getsource(cli._run_kanban_goal_loop_q)
    assert 'persist_user_display_kind="kanban_goal_continuation"' in src


