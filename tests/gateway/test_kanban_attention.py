import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from gateway.kanban_attention import (
    applies,
    is_urgent,
    load_attention_policy,
    render_digest,
)


def _config(**overrides):
    policy = {
        "enabled": True,
        "mode": "pm",
        "destinations": [
            {"profile": "first-mate", "platform": "telegram", "chat_id": "captain", "chat_type": "dm"}
        ],
    }
    policy.update(overrides)
    return {"kanban": {"notification_policy": policy}}


def test_policy_is_destination_scoped_and_defaults_off():
    sub = {"notifier_profile": "first-mate", "platform": "telegram", "chat_id": "captain"}
    assert not applies(load_attention_policy({}), sub)
    assert applies(load_attention_policy(_config()), sub)
    assert not applies(
        load_attention_policy(_config()),
        {**sub, "chat_id": "another-destination"},
    )
    with pytest.raises(ValueError):
        load_attention_policy(_config(destinations=[{"profile": "first-mate"}]))


def test_policy_can_scope_one_thread_without_affecting_siblings():
    policy = load_attention_policy(_config(destinations=[{
        "profile": "first-mate", "platform": "telegram",
        "chat_id": "captain", "chat_type": "group", "thread_id": "focus",
    }]))
    base = {
        "notifier_profile": "first-mate",
        "platform": "telegram",
        "chat_id": "captain",
        "chat_type": "group",
    }
    assert applies(policy, {**base, "thread_id": "focus"})
    assert not applies(policy, {**base, "thread_id": "other"})


def test_modes_and_copilot_focus_are_bounded():
    policy = load_attention_policy(
        _config(mode="copilot", focus_task_ids=["a", "b", "c", "d"])
    )
    assert policy.mode == "copilot"
    assert policy.focus_task_ids == ("a", "b", "c")
    assert load_attention_policy(_config(mode="unknown")).mode == "pm"
    assert load_attention_policy(_config(mode="brainstorm")).mode == "brainstorm"

    # `hermes config set path.0 ...` intentionally materializes numeric paths
    # as mappings; the loader accepts that CLI-native representation too.
    cli_policy = load_attention_policy({
        "kanban": {"notification_policy": {
            "enabled": True,
            "mode": "copilot",
            "destinations": {"0": {
                "profile": "first-mate", "platform": "telegram", "chat_id": "captain", "chat_type": "dm"
            }},
            "focus_task_ids": {"0": "a", "1": "b", "2": "c", "3": "d"},
        }}
    })
    assert cli_policy.focus_task_ids == ("a", "b", "c")
    assert cli_policy.destinations[0]["chat_id"] == "captain"


def test_genuine_captain_and_security_gates_are_immediate():
    needs_input = SimpleNamespace(block_kind="needs_input")
    assert is_urgent("blocked", {"reason": "Choose release A or B"}, needs_input)
    assert is_urgent("blocked", {"reason": "credential unavailable"}, None)
    assert is_urgent("blocked", {"reason": "security trust boundary failed"}, None)
    assert is_urgent("changes_requested", {"reason": "critical path regression"}, None)
    assert is_urgent(
        "completed", {"summary": "Final milestone requires Captain sign-off"}, None
    )


def test_brainstorm_queues_ordinary_needs_input_but_not_emergencies():
    needs_input = SimpleNamespace(block_kind="needs_input")
    assert not is_urgent(
        "blocked", {"reason": "Choose release A or B"}, needs_input, "brainstorm"
    )
    assert is_urgent(
        "blocked", {"reason": "Safety approval expires in 2 minutes"},
        needs_input, "brainstorm",
    )


def test_deliberate_pauses_are_not_urgent():
    task = SimpleNamespace(block_kind="needs_input")
    for reason in (
        "focus-pause while Captain is chatting",
        "deliberately parked; no-action",
        "duplicate card",
        "superseded by t_next",
    ):
        assert not is_urgent("blocked", {"reason": reason}, task)


def test_child_burst_rolls_up_to_one_parent_delta_and_deduplicates():
    rows = [
        {
            "task_id": f"t_child_{i}",
            "parent_id": "t_parent",
            "event_id": i,
            "kind": "completed",
        }
        for i in range(10)
    ]
    rows.append(dict(rows[0]))  # replayed duplicate
    digest = render_digest(rows, 900)
    assert digest.count("t_parent:") == 1
    assert "10 completed" in digest
    assert digest.count("t_child_0") == 1


def test_digest_is_bounded_and_redacts_credentials():
    rows = [
        {
            "task_id": "token=do-not-leak-" + ("x" * 200),
            "parent_id": f"family-{i}",
            "event_id": i,
            "kind": "completed",
        }
        for i in range(20)
    ]
    digest = render_digest(rows, 240)
    assert len(digest) <= 240
    assert "do-not-leak" not in digest
    assert "[REDACTED]" in digest


@pytest.mark.asyncio
async def test_ten_child_completions_send_one_parent_digest_without_network(
    tmp_path, monkeypatch
):
    from gateway.config import Platform
    from gateway.run import GatewayRunner
    from hermes_cli import kanban_db as kb

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    conn = kb.connect()
    try:
        parent = kb.create_task(conn, title="portfolio", assignee="orchestrator")
        kb.add_notify_sub(
            conn,
            task_id=parent,
            platform="telegram",
            chat_id="captain",
            notifier_profile="first-mate",
        )
        children = [
            kb.create_task(
                conn,
                title=f"research {i}",
                assignee="researcher",
                parents=[parent],
            )
            for i in range(10)
        ]
        for child in children:
            kb._append_event(
                conn, child, kind="completed", payload={"summary": "research complete"}
            )
    finally:
        conn.close()

    from gateway.session import SessionSource
    from gateway.conversation_modes import set_mode
    destination = SessionSource(
        platform=Platform.TELEGRAM, chat_id="captain", chat_type="dm",
        profile="first-mate",
    )
    set_mode(destination, "brainstorm")

    adapter = SimpleNamespace(send=AsyncMock(return_value=None), _active_sessions={})
    runner = GatewayRunner.__new__(GatewayRunner)
    runner._running = True
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner._profile_adapters = {"first-mate": {Platform.TELEGRAM: adapter}}
    runner._kanban_sub_fail_counts = {}
    runner._kanban_notifier_profile = "first-mate"
    runner._authorization_adapter = lambda platform, profile=None: adapter

    real_sleep = asyncio.sleep

    async def one_tick(delay):
        if delay == 5:
            return
        runner._running = False
        await real_sleep(0)

    with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=one_tick), patch(
        "hermes_cli.config.load_config", return_value=_config(interval_seconds=60)
    ):
        await runner._kanban_notifier_watcher(interval=1)

    adapter.send.assert_not_awaited()
    set_mode(destination, "pm")
    runner._running = True
    with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=one_tick), patch(
        "hermes_cli.config.load_config", return_value=_config(interval_seconds=60)
    ):
        await runner._kanban_notifier_watcher(interval=1)

    adapter.send.assert_awaited_once()
    text = adapter.send.await_args.args[1]
    assert parent in text
    assert "10 completed" in text

    # A fresh watcher process has no in-memory digest state, but the canonical
    # subscription cursor prevents an already-delivered delta from replaying.
    restarted_adapter = SimpleNamespace(send=AsyncMock(return_value=None), _active_sessions={})
    restarted = GatewayRunner.__new__(GatewayRunner)
    restarted._running = True
    restarted.adapters = {Platform.TELEGRAM: restarted_adapter}
    restarted._profile_adapters = {
        "first-mate": {Platform.TELEGRAM: restarted_adapter}
    }
    restarted._kanban_sub_fail_counts = {}
    restarted._kanban_notifier_profile = "first-mate"
    restarted._authorization_adapter = lambda platform, profile=None: restarted_adapter

    async def restarted_tick(delay):
        if delay == 5:
            return
        restarted._running = False
        await real_sleep(0)

    with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=restarted_tick), patch(
        "hermes_cli.config.load_config", return_value=_config(interval_seconds=60)
    ):
        await restarted._kanban_notifier_watcher(interval=1)
    restarted_adapter.send.assert_not_awaited()


@pytest.mark.parametrize("exit_mode", ["pm", "copilot"])
@pytest.mark.asyncio
async def test_shared_destination_brainstorm_exit_flushes_once(
    tmp_path, monkeypatch, exit_mode
):
    """A later delivery cannot erase an earlier transition in the same tick."""
    from gateway.config import Platform
    from gateway.conversation_modes import set_mode
    from gateway.run import GatewayRunner
    from gateway.session import SessionSource
    from hermes_cli import kanban_db as kb

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    conn = kb.connect()
    try:
        task_ids = [
            kb.create_task(conn, title=f"shared {index}", assignee="worker")
            for index in range(2)
        ]
        for task_id in task_ids:
            kb.add_notify_sub(
                conn, task_id=task_id, platform="telegram", chat_id="captain",
                notifier_profile="first-mate",
            )
            kb._append_event(conn, task_id, kind="completed", payload={"summary": "done"})
    finally:
        conn.close()

    destination = SessionSource(
        platform=Platform.TELEGRAM, chat_id="captain", chat_type="dm",
        profile="first-mate",
    )
    set_mode(destination, "brainstorm")
    adapter = SimpleNamespace(send=AsyncMock(return_value=None), _active_sessions={})
    runner = GatewayRunner.__new__(GatewayRunner)
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner._profile_adapters = {"first-mate": {Platform.TELEGRAM: adapter}}
    runner._kanban_sub_fail_counts = {}
    runner._kanban_notifier_profile = "first-mate"
    runner._authorization_adapter = lambda platform, profile=None: adapter
    real_sleep = asyncio.sleep

    async def run_tick():
        runner._running = True

        async def one_tick(delay):
            if delay == 5:
                return
            runner._running = False
            await real_sleep(0)

        with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=one_tick), patch(
            "hermes_cli.config.load_config", return_value=_config(interval_seconds=3600)
        ):
            await runner._kanban_notifier_watcher(interval=1)

    await run_tick()
    adapter.send.assert_not_awaited()

    focuses = task_ids if exit_mode == "copilot" else None
    set_mode(destination, exit_mode, focus=focuses)
    destination_key = ("first-mate", "telegram", "captain", "dm", "")
    runner._kanban_attention_last_digest = {destination_key: 10**30}
    await run_tick()

    adapter.send.assert_awaited_once()
    digest = adapter.send.await_args.args[1]
    assert all(task_id in digest for task_id in task_ids)

    # Both subscription claims advanced atomically; another tick cannot replay.
    await run_tick()
    adapter.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_active_conversation_defers_routine_digest_but_not_captain_gate(
    tmp_path, monkeypatch
):
    from gateway.config import Platform
    from gateway.run import GatewayRunner
    from hermes_cli import kanban_db as kb

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    conn = kb.connect()
    try:
        routine = kb.create_task(conn, title="routine", assignee="worker")
        urgent = kb.create_task(conn, title="gate", assignee="worker")
        for task_id in (routine, urgent):
            kb.add_notify_sub(
                conn, task_id=task_id, platform="telegram", chat_id="captain",
                notifier_profile="first-mate",
            )
        kb._append_event(conn, routine, kind="completed", payload={"summary": "done"})
        kb.block_task(conn, urgent, reason="Captain must choose A or B", kind="needs_input")
    finally:
        conn.close()

    from gateway.session import SessionSource, build_session_key

    active_key = build_session_key(SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="captain",
        chat_type="dm",
        profile="first-mate",
    ), profile="first-mate")
    adapter = SimpleNamespace(
        send=AsyncMock(return_value=None), _active_sessions={active_key: object()}
    )
    runner = GatewayRunner.__new__(GatewayRunner)
    runner._running = True
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner._profile_adapters = {"first-mate": {Platform.TELEGRAM: adapter}}
    runner._kanban_sub_fail_counts = {}
    runner._kanban_notifier_profile = "first-mate"
    runner._authorization_adapter = lambda platform, profile=None: adapter
    real_sleep = asyncio.sleep

    async def one_tick(delay):
        if delay == 5:
            return
        runner._running = False
        await real_sleep(0)

    with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=one_tick), patch(
        "hermes_cli.config.load_config", return_value=_config(interval_seconds=60)
    ):
        await runner._kanban_notifier_watcher(interval=1)

    # The urgent gate interrupts, while routine telemetry remains queued and
    # does not interleave with the Captain's active conversation.
    assert adapter.send.await_count == 1
    messages = [call.args[1] for call in adapter.send.await_args_list]
    assert any("Captain must choose" in message for message in messages)
    assert not any("Kanban digest" in message for message in messages)


def test_unrelated_active_chat_does_not_defer_destination():
    from gateway.config import Platform
    from gateway.kanban_watchers import _destination_has_active_session
    from gateway.session import SessionSource, build_session_key

    other_key = build_session_key(SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="someone-else",
        chat_type="group",
        profile="first-mate",
    ), profile="first-mate")
    adapter = SimpleNamespace(_active_sessions={other_key: object()})
    sub = {
        "notifier_profile": "first-mate",
        "chat_id": "captain",
        "chat_type": "group",
    }
    assert not _destination_has_active_session(adapter, sub, Platform.TELEGRAM)


@pytest.mark.asyncio
async def test_mixed_urgent_and_routine_atomic_claim_loses_neither(
    tmp_path, monkeypatch
):
    from gateway.config import Platform
    from gateway.run import GatewayRunner
    from hermes_cli import kanban_db as kb

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    kb.init_db()
    conn = kb.connect()
    try:
        task_id = kb.create_task(conn, title="mixed", assignee="worker")
        kb.add_notify_sub(
            conn, task_id=task_id, platform="telegram", chat_id="captain",
            notifier_profile="first-mate",
        )
        kb._append_event(conn, task_id, kind="completed", payload={"summary": "routine"})
        kb.block_task(conn, task_id, reason="Captain must choose A", kind="needs_input")
    finally:
        conn.close()

    adapter = SimpleNamespace(send=AsyncMock(return_value=None), _active_sessions={})
    runner = GatewayRunner.__new__(GatewayRunner)
    runner._running = True
    runner.adapters = {Platform.TELEGRAM: adapter}
    runner._profile_adapters = {"first-mate": {Platform.TELEGRAM: adapter}}
    runner._kanban_sub_fail_counts = {}
    runner._kanban_notifier_profile = "first-mate"
    runner._authorization_adapter = lambda platform, profile=None: adapter
    real_sleep = asyncio.sleep

    async def one_tick(delay):
        if delay == 5:
            return
        runner._running = False
        await real_sleep(0)

    with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=one_tick), patch(
        "hermes_cli.config.load_config", return_value=_config(interval_seconds=60)
    ):
        await runner._kanban_notifier_watcher(interval=1)

    messages = [call.args[1] for call in adapter.send.await_args_list]
    assert any(" done" in message and "routine" in message for message in messages)
    assert any("Captain must choose" in message for message in messages)
    assert not any("Kanban digest" in message for message in messages)

    adapter.send.reset_mock()
    runner._running = True
    with patch("gateway.kanban_watchers.asyncio.sleep", side_effect=one_tick), patch(
        "hermes_cli.config.load_config", return_value=_config(interval_seconds=60)
    ):
        await runner._kanban_notifier_watcher(interval=1)
    adapter.send.assert_not_awaited()
