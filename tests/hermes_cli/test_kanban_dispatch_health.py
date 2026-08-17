from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

from hermes_cli import kanban_db as kb


def test_missing_reviewer_profile_persists_reason_and_coalesces_sla(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes_cli import profiles

    monkeypatch.setattr(profiles, "profile_exists", lambda _name: False)
    with kb.connect(db_path=tmp_path / "missing.db") as conn:
        task_id = kb.create_task(conn, title="review", assignee="reviewer")
        old = int(time.time()) - kb.DEFAULT_CLAIM_SLA_SECONDS - 10
        conn.execute(
            "UPDATE tasks SET ready_since = ? WHERE id = ?", (old, task_id)
        )

        first = kb.dispatch_once(conn, spawn_fn=lambda *_args: 1)
        task = kb.get_task(conn, task_id)
        assert task is not None
        assert task.status == "ready"
        assert task.dispatch_reason == "nonspawnable_profile"
        assert task.dispatch_attempt_count == 1
        assert task.last_considered_at is not None
        assert first.claim_sla_breached == [
            (task_id, "nonspawnable_profile", kb.DEFAULT_CLAIM_SLA_SECONDS + 10)
        ]

        second = kb.dispatch_once(conn, spawn_fn=lambda *_args: 1)
        task = kb.get_task(conn, task_id)
        assert task is not None
        assert task.dispatch_attempt_count == 2
        assert second.claim_sla_breached == []
        events = [e for e in kb.list_events(conn, task_id) if e.kind == "dispatch_claim_sla"]
        assert len(events) == 1


def test_poison_head_does_not_prevent_dispatchable_reviewer_canary(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes_cli import profiles

    monkeypatch.setattr(profiles, "profile_exists", lambda name: name == "reviewer")
    spawned: list[str] = []

    def spawn(task, _workspace):
        spawned.append(task.id)
        return 4242

    with kb.connect(db_path=tmp_path / "poison.db") as conn:
        poison = kb.create_task(conn, title="bad lane", assignee="missing", priority=100)
        canary = kb.create_task(conn, title="reviewer no-op canary", assignee="reviewer")
        result = kb.dispatch_once(conn, spawn_fn=spawn)

        assert result.skipped_nonspawnable == [poison]
        assert spawned == [canary]
        poison_task = kb.get_task(conn, poison)
        assert poison_task is not None
        assert poison_task.dispatch_reason == "nonspawnable_profile"
        claimed = kb.get_task(conn, canary)
        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.dispatch_reason == "claimable"
        assert kb.complete_task(conn, canary, expected_run_id=claimed.current_run_id)
        completed = kb.get_task(conn, canary)
        assert completed is not None
        assert completed.status == "done"


def test_global_capacity_records_every_ready_task_without_claiming(
    tmp_path: Path, all_assignees_spawnable
) -> None:
    with kb.connect(db_path=tmp_path / "capacity.db") as conn:
        running_id = kb.create_task(conn, title="running", assignee="worker")
        assert kb.claim_task(conn, running_id) is not None
        waiting = [
            kb.create_task(conn, title=f"waiting {index}", assignee="reviewer")
            for index in range(2)
        ]

        result = kb.dispatch_once(conn, max_in_progress=1, spawn_fn=lambda *_args: 1)
        assert result.spawned == []
        for task_id in waiting:
            task = kb.get_task(conn, task_id)
            assert task is not None
            assert task.status == "ready"
            assert task.dispatch_reason == "global_capacity"
            assert task.dispatch_attempt_count == 1


def test_spawn_failure_starts_a_fresh_claim_sla_episode(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes_cli import profiles

    monkeypatch.setattr(profiles, "profile_exists", lambda _name: True)
    db_path = tmp_path / "spawn-retry.db"
    with kb.connect(db_path=db_path) as conn:
        task_id = kb.create_task(conn, title="retry", assignee="worker")
        old = int(time.time()) - kb.DEFAULT_CLAIM_SLA_SECONDS - 2
        conn.execute("UPDATE tasks SET ready_since = ? WHERE id = ?", (old, task_id))
        first = kb.dispatch_once(conn, spawn_fn=lambda *_args: (_ for _ in ()).throw(RuntimeError("boom")))
        assert first.claim_sla_breached == []  # claimed before the SLA batch flushed
        retried = kb.get_task(conn, task_id)
        assert retried is not None and retried.status == "ready"
        assert retried.dispatch_attempt_count == 1
        assert retried.dispatch_sla_alerted_at is None
        assert retried.ready_since is not None and retried.ready_since > old

        conn.execute("UPDATE tasks SET ready_since = ? WHERE id = ?", (old, task_id))
        monkeypatch.setattr(profiles, "profile_exists", lambda _name: False)
        second = kb.dispatch_once(conn, spawn_fn=lambda *_args: 1)
        assert len(second.claim_sla_breached) == 1

    with kb.connect(db_path=db_path) as reopened:
        persisted = kb.get_task(reopened, task_id)
        assert persisted is not None
        assert persisted.dispatch_reason == "nonspawnable_profile"
        assert persisted.dispatch_sla_alerted_at is not None


def test_review_changes_ready_starts_a_fresh_episode(
    tmp_path: Path, monkeypatch
) -> None:
    from hermes_cli import profiles

    monkeypatch.setattr(profiles, "profile_exists", lambda _name: False)
    with kb.connect(db_path=tmp_path / "review-episode.db") as conn:
        task_id = kb.create_task(conn, title="review loop", assignee="implementer")
        assert kb.request_review(conn, task_id, reviewer="reviewer")
        old = int(time.time()) - kb.DEFAULT_CLAIM_SLA_SECONDS - 3
        conn.execute("UPDATE tasks SET ready_since = ? WHERE id = ?", (old, task_id))
        assert len(kb.dispatch_once(conn).claim_sla_breached) == 1

        claimed = kb.claim_review_task(conn, task_id)
        assert claimed is not None
        ok, implementer = kb.request_changes(
            conn, task_id, reason="repair", expected_run_id=claimed.current_run_id,
        )
        assert ok and implementer == "implementer"
        waiting = kb.get_task(conn, task_id)
        assert waiting is not None and waiting.status == "ready"
        assert waiting.dispatch_sla_alerted_at is None
        assert waiting.dispatch_attempt_count == 0

        conn.execute("UPDATE tasks SET ready_since = ? WHERE id = ?", (old, task_id))
        assert len(kb.dispatch_once(conn).claim_sla_breached) == 1
        events = [e for e in kb.list_events(conn, task_id) if e.kind == "dispatch_claim_sla"]
        assert len(events) == 2


def test_zero_capacity_persistence_is_bounded_and_rotates(
    tmp_path: Path, all_assignees_spawnable, monkeypatch
) -> None:
    with kb.connect(db_path=tmp_path / "bounded.db") as conn:
        running = kb.create_task(conn, title="running", assignee="worker")
        assert kb.claim_task(conn, running)
        queued = [
            kb.create_task(conn, title=f"queued {index}", assignee="worker")
            for index in range(kb.DISPATCH_HEALTH_BATCH_LIMIT + 7)
        ]
        original_write_txn = kb.write_txn
        write_transactions = 0

        @contextmanager
        def counted_write_txn(*args, **kwargs):
            nonlocal write_transactions
            write_transactions += 1
            with original_write_txn(*args, **kwargs):
                yield

        monkeypatch.setattr(kb, "write_txn", counted_write_txn)
        first = kb.dispatch_once(conn, max_in_progress=1)
        assert first.spawned == []
        # Two fixed maintenance transactions plus one batched telemetry write;
        # the queue length does not add per-task writer transactions.
        assert write_transactions == 3
        first_tasks = [kb.get_task(conn, task_id) for task_id in queued]
        assert all(task is not None for task in first_tasks)
        considered_first = [
            task for task in first_tasks
            if task is not None and task.dispatch_attempt_count == 1
        ]
        assert len(considered_first) == kb.DISPATCH_HEALTH_BATCH_LIMIT

        kb.dispatch_once(conn, max_in_progress=1)
        assert write_transactions == 6
        second_tasks = [kb.get_task(conn, task_id) for task_id in queued]
        assert all(
            task is not None and task.dispatch_attempt_count >= 1
            for task in second_tasks
        )


def test_per_profile_cap_preserves_dispatch_health_for_other_profiles(
    tmp_path: Path, all_assignees_spawnable
) -> None:
    spawned: list[str] = []
    with kb.connect(db_path=tmp_path / "profile-health.db") as conn:
        running = kb.create_task(conn, title="worker running", assignee="worker")
        assert kb.claim_task(conn, running)
        capped = kb.create_task(conn, title="worker queued", assignee="worker")
        available = kb.create_task(conn, title="reviewer queued", assignee="reviewer")

        result = kb.dispatch_once(
            conn,
            max_in_progress_per_profile=1,
            spawn_fn=lambda task, *_args: spawned.append(task.id) or 4242,
        )

        assert result.skipped_per_profile_capped == [(capped, "worker", 1)]
        assert spawned == [available]
        capped_task = kb.get_task(conn, capped)
        available_task = kb.get_task(conn, available)
        assert capped_task is not None
        assert capped_task.dispatch_reason == "profile_capacity"
        assert capped_task.dispatch_attempt_count == 1
        assert available_task is not None
        assert available_task.status == "running"
        assert available_task.dispatch_reason == "claimable"


def test_critical_memory_guard_records_bounded_fair_health(
    tmp_path: Path, all_assignees_spawnable, monkeypatch
) -> None:
    monkeypatch.setattr(kb, "_memory_pressure_level", lambda: "critical")
    with kb.connect(db_path=tmp_path / "memory-health.db") as conn:
        queued = [
            kb.create_task(conn, title=f"queued {index}", assignee="worker")
            for index in range(kb.DISPATCH_HEALTH_BATCH_LIMIT + 1)
        ]

        first = kb.dispatch_once(conn)
        assert first.memory_pressure == "critical"
        assert first.spawned == []
        tasks = [kb.get_task(conn, task_id) for task_id in queued]
        assert all(task is not None for task in tasks)
        considered = [
            task for task in tasks
            if task is not None and task.dispatch_attempt_count == 1
        ]
        assert len(considered) == kb.DISPATCH_HEALTH_BATCH_LIMIT
        assert all(
            task.dispatch_reason == "memory_pressure:critical"
            for task in considered
        )

        kb.dispatch_once(conn)
        last = kb.get_task(conn, queued[-1])
        assert last is not None
        assert last.dispatch_attempt_count == 1
